import os
import json
import logging
import joblib
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import func
from models import Event, AIInteraction, AISuggestion, ChunkDecision, EditorEvent, Session, SessionScore
from llm import GeminiClient

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    'rate_acceptance',
    'duration_deliberation_avg',
    'rate_post_acceptance_edit',
    'freq_verification',
    'ratio_reprompt',
    'rate_chunk_acceptance',
    'rate_passive_acceptance',
    'duration_chunk_avg_ms',
    'pct_time_editor',
    'pct_time_chat',
    'duration_orientation_s',
    'depth_iteration',
    'count_prompt_orientation',
    'count_prompt_implementation',
    'count_prompt_verification'
]

_MODELS_CACHE = {}

def load_models():
    """Load XGBoost models from disk."""
    global _MODELS_CACHE
    if _MODELS_CACHE:
        return _MODELS_CACHE

    base_path = os.path.dirname(__file__)
    
    # Use environment variable if provided, fallback to standard shared location
    artifacts_dir = os.environ.get(
        "MODEL_ARTIFACTS_DIR", 
        os.path.join(os.path.dirname(base_path), "model", "models")
    )

    paths = [artifacts_dir, os.path.join(base_path, "models")]

    for p in paths:
        c1_path = os.path.join(p, "component1_xgboost.joblib")
        c2_path = os.path.join(p, "component2_xgboost.joblib")
        
        if os.path.exists(c1_path) and os.path.exists(c2_path):
            try:
                _MODELS_CACHE['c1'] = joblib.load(c1_path)
                _MODELS_CACHE['c2'] = joblib.load(c2_path)
                logger.info(f"Loaded models from {p}")
                return _MODELS_CACHE
            except Exception as e:
                logger.error(f"Error loading models from {p}: {e}")

    logger.warning("Models not found in standard paths.")
    return {}

def extract_c1_features(session_id, db) -> np.ndarray:
    """
    Query the database and delegate to the unified model.features extractor.
    """
    import sys
    import os
    maddata_dir = os.path.dirname(os.path.dirname(__file__))
    if maddata_dir not in sys.path:
        sys.path.append(maddata_dir)
    from model.features import extract_c1_features as unified_extractor
    
    session = db.query(Session).filter_by(session_id=session_id).first()
    if not session:
        return np.zeros(len(FEATURE_NAMES))

    # Fetch raw materials from DB
    decisions = db.query(ChunkDecision).filter_by(session_id=session_id).all()
    events = db.query(Event).filter_by(session_id=session_id).all()
    interactions = db.query(AIInteraction).filter_by(session_id=session_id).all()

    # Convert SQLAlchemy objects to simple dicts for the shared logic
    data = {
        'decisions': [
            {
                'decision': d.decision,
                'time_on_chunk_ms': d.time_on_chunk_ms,
                'proposed_code': d.proposed_code,
                'final_code': d.final_code
            } for d in decisions
        ],
        'events': [
            {
                'event_type': e.event_type,
                'content': e.content,
                'timestamp': e.timestamp
            } for e in events
        ],
        'interactions': [
            {
                'phase': p.phase,
                'shown_at': p.shown_at
            } for p in interactions
        ],
        'session_start': session.started_at
    }

    return unified_extractor(data)

def run_component1(session_id, db) -> dict:
    models = load_models()
    features = extract_c1_features(session_id, db)
    
    if 'c1' not in models:
        # Fallback to a neutral prediction if model missing
        return {
            "label": "balanced", 
            "score": 3.0, 
            "features": features.tolist(),
            "fallback": True
        }
    
    # Predict label
    label = models['c1'].predict(features.reshape(1, -1))[0]
    # Map label string to a numeric score for aggregation
    label_map = {"over_reliant": 1.5, "balanced": 3.0, "strategic": 4.5}
    score = label_map.get(str(label), 3.0)
    
    return {
        "label": str(label),
        "score": score,
        "features": features.tolist(),
        "fallback": False
    }

def run_component2(session_id, db) -> dict:
    """
    Scores prompt quality. 
    Ideally this uses prompt_features.py logic.
    """
    prompts = db.query(AIInteraction).filter_by(session_id=session_id).all()
    if not prompts:
        return {"score": 3.0, "per_prompt": []}
    
    scores = []
    for p in prompts:
        # Mirroring heuristic from model/prompt_features.py
        base_score = 1.0
        text = p.prompt or ""
        if len(text) > 20: base_score += 1.0
        if len(text) > 50: base_score += 0.5
        if '`' in text: base_score += 1.0
        # camelCase/snake_case check
        if any(c.isupper() for c in text) or '_' in text: base_score += 0.5
        
        scores.append(min(5.0, base_score))
    
    avg = sum(scores) / len(scores)
    return {"score": avg, "per_prompt": scores}

def run_component3(session_id, db) -> dict:
    """
    Component 3 measures Critical Review.
    Heuristic: high score for 'modified' and 'rejected', low for 'accepted'.
    """
    decisions = db.query(ChunkDecision).filter_by(session_id=session_id).all()
    if not decisions:
        return {"score": 3.0}
    
    scores = []
    for d in decisions:
        if d.decision == 'accepted':
            # Passive acceptance: 2.0
            scores.append(2.0)
        elif d.decision == 'modified':
            # Substantial review: 4.5
            scores.append(4.5)
        elif d.decision == 'rejected':
            # Critical rejection: 4.0
            scores.append(4.0)
            
    avg = sum(scores) / len(scores)
    return {"score": avg}

def aggregate_scores(c1, c2, c3):
    """
    Mirrors model/aggregation.py
    """
    w1, w2, w3 = 0.34, 0.33, 0.33
    weighted = (c1['score'] * w1) + (c2['score'] * w2) + (c3['score'] * w3)
    
    if weighted >= 3.5:
        label = "strategic"
    elif weighted >= 2.5:
        label = "balanced"
    else:
        label = "over_reliant"
        
    return round(float(weighted), 2), label

def build_judge_excerpt(session_id, db) -> str:
    """
    Build a textual summary of the session for the LLM judge.
    Includes key prompts and significant code modifications.
    """
    excerpts = []
    
    # 1. Significant Prompts
    prompts = db.query(AIInteraction).filter_by(session_id=session_id).all()
    if prompts:
        excerpts.append("KEY PROMPTS:")
        for i, p in enumerate(prompts[:5]): # Top 5 for context limit
            excerpts.append(f"  {i+1}. {p.prompt[:200]}...")
            
    # 2. Modified/Rejected Suggestions
    decisions = db.query(ChunkDecision).filter(
        ChunkDecision.session_id == session_id,
        ChunkDecision.decision.in_(['modified', 'rejected'])
    ).all()
    if decisions:
        excerpts.append("\nCRITICAL REVIEW MOMENTS:")
        for d in decisions[:3]:
            excerpts.append(f"  - Decision: {d.decision}")
            if d.decision == 'modified':
                excerpts.append(f"    Code change: {len(d.proposed_code)} chars -> {len(d.final_code)} chars")
                
    # 3. Execution Summary
    execs = db.query(Event).filter_by(session_id=session_id, event_type='execute').all()
    if execs:
        pass_count = len([e for e in execs if '"exit_code": 0' in (e.metadata_ or "")])
        excerpts.append(f"\nEXECUTION SUMMARY: {len(execs)} runs, {pass_count} successful.")

    return "\n".join(excerpts)

def trigger_scoring(session_id, db):
    """
    Runs the full scoring pipeline and starts the async judge task.
    """
    try:
        c1 = run_component1(session_id, db)
        c2 = run_component2(session_id, db)
        c3 = run_component3(session_id, db)
        
        weighted_score, label = aggregate_scores(c1, c2, c3)
        
        score_id = str(uuid_4_placeholder()) # We'll fetch uuid from uuid module in a bit or just use uuid.uuid4()
        import uuid
        score_id = str(uuid.uuid4())
        
        # Prepare scores serialization
        score_record = SessionScore(
            score_id=score_id,
            session_id=session_id,
            computed_at=datetime.now(timezone.utc),
            structural_scores=json.dumps(c1),
            prompt_quality_scores=json.dumps(c2),
            review_scores=json.dumps(c3),
            overall_label=label,
            weighted_score=weighted_score,
            fallback_components=json.dumps(["c1"] if c1.get("fallback") else [])
        )
        db.add(score_record)
        db.commit()
        
        # Build excerpts and trigger async judge
        excerpts = build_judge_excerpt(session_id, db)
        scores_for_judge = {
            "c1": c1.get("score"),
            "c2": c2.get("score"),
            "c3": c3.get("score"),
            "weighted": weighted_score,
            "label": label
        }
        
        threading.Thread(
            target=async_judge_task,
            args=(session_id, score_id, scores_for_judge, excerpts),
            daemon=True
        ).start()
        
        return score_id
        
    except Exception as e:
        logger.error(f"Scoring pipeline failed for session {session_id}: {e}")
        db.rollback()
        return None

def async_judge_task(session_id, score_id, scores_dict, excerpts):
    """
    Background task to call Gemini judge and update the score record.
    """
    from db import SessionLocal # Import here to avoid circular dependencies
    db = SessionLocal()
    try:
        client = GeminiClient()
        system_prompt = (
            "You are a senior technical interviewer. Analyze the provided session metrics "
            "and excerpts to write a professional, balanced 2-3 paragraph 'Narrative Report' "
            "about the candidate's balance between independent thought and AI assistance. "
            "Use the RUBRIC and OVERALL LABELS provided in context."
        )
        
        narrative = client.judge_call(scores_dict, excerpts, system_prompt)
        
        score_record = db.query(SessionScore).filter_by(score_id=score_id).first()
        if score_record:
            score_record.llm_narrative = narrative
            db.commit()
            logger.info(f"Narrative generated for session {session_id}")
            
    except Exception as e:
        logger.error(f"Async judge task failed for session {session_id}: {e}")
        db.rollback()
    finally:
        db.close()

def uuid_4_placeholder():
    import uuid
    return uuid.uuid4()
