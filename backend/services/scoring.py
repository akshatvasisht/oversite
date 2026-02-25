import os
import uuid
import json
import logging
import joblib
import threading
import numpy as np
import pandas as pd
import shap
from datetime import datetime, timezone
from sqlalchemy import func
from schema import Event, AIInteraction, AISuggestion, ChunkDecision, EditorEvent, Session, SessionScore
from services.llm import GeminiClient

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
    'count_prompt_verification',
    'deliberation_to_action_ratio'
]

_MODELS_CACHE = {}
_SHAP_EXPL_CACHE = {}

def load_models():
    """
    Retrieves and caches pre-trained XGBoost classifiers from storage.

    Returns:
        A dictionary containing 'behavioral' and 'prompt_quality' model instances.
    """
    global _MODELS_CACHE
    if _MODELS_CACHE:
        return _MODELS_CACHE

    if os.environ.get("SCORING_FALLBACK_MODE", "false").lower() == "true":
        logger.warning("SCORING_FALLBACK_MODE is true. Bypassing model loading.")
        return {}

    base_path = os.path.dirname(__file__)
    
    # Use environment variable if provided, fallback to standard shared location
    artifacts_dir = os.environ.get(
        "MODEL_ARTIFACTS_DIR", 
        os.path.join(os.path.dirname(os.path.dirname(base_path)), "model", "models")
    )

    paths = [artifacts_dir, os.path.join(base_path, "models")]

    for p in paths:
        behavioral_path = os.path.join(p, "behavioral_classifier.joblib")
        prompt_path = os.path.join(p, "prompt_quality_classifier.joblib")
        
        if os.path.exists(behavioral_path) and os.path.exists(prompt_path):
            try:
                _MODELS_CACHE['behavioral'] = joblib.load(behavioral_path)
                _MODELS_CACHE['prompt_quality'] = joblib.load(prompt_path)
                logger.info(f"Loaded models from {p}")
                return _MODELS_CACHE
            except Exception as e:
                logger.error(f"Error loading models from {p}: {e}")

    logger.warning("Models not found in standard paths.")
    return {}

def extract_behavioral_features(session_id, db) -> np.ndarray:
    """
    Query the database and delegate to the unified model.features extractor.
    """
    import sys
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        
    from model.features import extract_behavioral_features as unified_extractor
    
    session = db.query(Session).filter_by(session_id=session_id).first()
    if not session:
        return np.zeros(len(FEATURE_NAMES))

    # Fetch raw materials from DB
    decisions = db.query(ChunkDecision).filter_by(session_id=session_id).all()
    events = db.query(Event).filter_by(session_id=session_id).all()
    interactions = db.query(AIInteraction).filter_by(session_id=session_id).all()

    # Map SQLAlchemy objects to the strict SessionTelemetry contract
    from model.features import SessionTelemetry
    
    telemetry: SessionTelemetry = {
        'decisions': [d.to_dict() for d in decisions],
        'events': [e.to_dict() for e in events],
        'interactions': [i.to_dict() for i in interactions],
        'session_start': session.started_at
    }

    return unified_extractor(telemetry)

def run_behavioral_evaluation(session_id: str, db) -> dict:
    """
    Evaluates candidate behavior using structural telemetry features.

    Args:
        session_id: The session to analyze.
        db: Active database session.

    Returns:
        A dictionary containing the predicted label and normalized confidence score.
    """
    models = load_models()
    features = extract_behavioral_features(session_id, db)
    
    if 'behavioral' not in models:
        # Fallback to a neutral prediction if model missing
        return {
            "label": "balanced", 
            "score": 3.0, 
            "features": features.tolist(),
            "fallback": True
        }
    
    # Subset the features to only the structural ones the model was trained on
    # Using normalized prompt ratios: orientation, implementation, verification
    model = models['behavioral']
    structural_indices = [12, 13, 14]
    X_structural = features[structural_indices].reshape(1, -1)
    
    # Predict behavioral label
    raw_label = model.predict(X_structural)
    label = int(raw_label[0]) # Force cast to plain int
    
    # Calculate SHAP values for local explanation (on the structural features ONLY)
    # For CalibratedClassifierCV, we extract SHAP from the ensemble or a member.
    # Here we use the base estimator of the first ensemble member for simplicity in feature mapping.
    base_est = model.calibrated_classifiers_[0].estimator
    explainer = shap.TreeExplainer(base_est)
    shap_values = explainer.shap_values(X_structural)
    
    # Debug logging (safe for production if kept minimal)
    logger.debug(f"Label: {label}, SHAP Values Type: {type(shap_values)}")
    
    # Handle multi-class SHAP output
    # For multi-class, shap_values is a list of [n_samples, n_features] arrays
    try:
        if isinstance(shap_values, list):
            class_shap = shap_values[int(label)][0]
        elif isinstance(shap_values, np.ndarray) and len(shap_values.shape) == 3:
            # Shape is likely (n_samples, n_classes, n_features)
            class_shap = shap_values[0][int(label)]
        else:
            # Binary or single-label fallback
            class_shap = shap_values[0]
    except Exception as e:
        logger.error(f"SHAP indexing failed: {e}. SHAP shape: {getattr(shap_values, 'shape', 'N/A')}")
        class_shap = np.zeros(len(structural_indices))
    
    explanations = []
    # Sort by absolute magnitude
    sorted_indices = np.argsort(np.abs(class_shap))[::-1]
    for idx in sorted_indices[:3]: # Top 3 structural drivers
        orig_feat_idx = structural_indices[idx]
        impact = "increases" if class_shap[idx] > 0 else "decreases"
        importance = abs(float(class_shap[idx]))
        explanations.append({
            "feature": FEATURE_NAMES[orig_feat_idx],
            "impact": impact,
            "contribution": importance,
            "value": float(features[orig_feat_idx])
        })

    # Core Metrics for grounding (The Judge Path - raw session telemetry)
    core_metrics = {
        "rate_acceptance": float(features[0]),
        "duration_deliberation_avg": float(features[1]),
        "rate_post_acceptance_edit": float(features[2]),
        "deliberation_to_action_ratio": float(features[15])
    }

    # Map label integer to string and numeric score for aggregation
    LABEL_NAMES_MAP = {0: "over_reliant", 1: "balanced", 2: "strategic"}
    label_str = LABEL_NAMES_MAP.get(label, "balanced")
    
    label_score_map = {"over_reliant": 1.5, "balanced": 3.0, "strategic": 4.5}
    score = label_score_map.get(label_str, 3.0)
    
    return {
        "label": label_str,
        "score": score,
        "features": features.tolist(),
        "explanations": explanations,
        "core_metrics": core_metrics,
        "fallback": False
    }

def run_prompt_evaluation(session_id: str, db) -> dict:
    """
    Evaluates the engineering quality of user-AI prompts.

    Args:
        session_id: The session to analyze.
        db: Active database session.

    Returns:
        A dictionary containing the prompt proficiency score and label.
    """
    import sys
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        
    from model.prompt_features import score_prompts
    
    models = load_models()
    interactions = db.query(AIInteraction).filter_by(session_id=session_id).all()
    
    if not interactions:
        return {"score": 3.0, "per_prompt": [], "fallback": 'prompt_quality' not in models}
    
    prompt_list = [p.prompt or "" for p in interactions]
    scores = score_prompts(prompt_list)
    
    avg = sum(scores) / len(scores) if scores else 3.0
    
    return {
        "score": avg, 
        "per_prompt": scores,
        "fallback": 'prompt_quality' not in models
    }

def run_critical_review_evaluation(session_id: str, db) -> dict:
    """
    Measures the candidate's active engagement with AI suggestions.

    Args:
        session_id: The session to analyze.
        db: Active database session.

    Returns:
        A dictionary containing edit-distance metrics and engagement labels.
    """
    # Critical review is measured as a deterministic fallback when direct engagement is detectable.
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

def aggregate_scores(behavioral, prompt, critical):
    """
    Synthesizes multiple scoring dimensions into a unified assessment.

    Args:
        behavioral: Result dictionary from behavioral evaluation.
        prompt: Result dictionary from prompt evaluation.
        critical: Result dictionary from critical review evaluation.

    Returns:
        A tuple of (weighted_score, overall_label).
    """
    w1, w2, w3 = 0.34, 0.33, 0.33
    weighted = (behavioral['score'] * w1) + (prompt['score'] * w2) + (critical['score'] * w3)
    
    if weighted >= 3.5:
        label = "strategic"
    elif weighted >= 2.5:
        label = "balanced"
    else:
        label = "over_reliant"
        
    return round(float(weighted), 2), label

def build_judge_excerpt(session_id: str, db) -> str:
    """
    Constructs a highly-contextual textual summary for the LLM judge.

    Args:
        session_id: The session to summarize.
        db: Active database session.

    Returns:
        A multiline string containing top prompts, critical review moments, 
        and execution outcomes.
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

def trigger_scoring(session_id: str, db):
    """
    Coordinates the multi-stage evaluation pipeline for a session.

    Args:
        session_id: The unique identifier of the session to evaluate.
        db: Active database session for retrieving telemetry and storing results.

    Returns:
        The ID of the generated SessionScore record, or None on failure.
    """
    try:
        events_count = db.query(Event).filter_by(session_id=session_id).count()
        prompts_count = db.query(AIInteraction).filter_by(session_id=session_id).count()
        
        if events_count == 0 and prompts_count == 0:
            behavioral = {"score": 3.0, "fallback": True, "label": "balanced"}
            prompt = {"score": 3.0}
            critical = {"score": 3.0}
            weighted_score = 3.0
            label = "Not Enough Data"
        else:
            behavioral = run_behavioral_evaluation(session_id, db)
            prompt = run_prompt_evaluation(session_id, db)
            critical = run_critical_review_evaluation(session_id, db)
            
            weighted_score, label = aggregate_scores(behavioral, prompt, critical)
        
        score_id = str(uuid.uuid4())
        
        # Store only numeric/scalar fields — strip features array and booleans
        behavioral_display = {"score": behavioral.get("score", 0), "label": behavioral.get("label", "")}
        prompt_display = {"score": prompt.get("score", 0)}
        critical_display = {"score": critical.get("score", 0)}

        # Prepare scores serialization
        score_record = SessionScore(
            score_id=score_id,
            session_id=session_id,
            computed_at=datetime.now(timezone.utc),
            structural_scores=json.dumps(behavioral_display),
            prompt_quality_scores=json.dumps(prompt_display),
            review_scores=json.dumps(critical_display),
            overall_label=label,
            weighted_score=weighted_score,
            fallback_components=json.dumps(["behavioral"] if behavioral.get("fallback") else [])
        )
        db.add(score_record)
        db.commit()
        
        # Build excerpts and trigger async judge
        excerpts = build_judge_excerpt(session_id, db)
        scores_for_judge = {
            "behavioral": behavioral.get("score"),
            "prompt_quality": prompt.get("score"),
            "critical_review": critical.get("score"),
            "weighted": weighted_score,
            "label": label
        }
        
        threading.Thread(
            target=async_judge_task,
            args=(session_id, score_id, scores_for_judge, excerpts, behavioral.get("explanations", []), behavioral.get("core_metrics", {})),
            daemon=True
        ).start()
        
        return score_id
        
    except Exception as e:
        logger.error(f"Scoring pipeline failed for session {session_id}: {e}")
        db.rollback()
        return None

def async_judge_task(session_id: str, score_id: str, scores_dict: dict, excerpts: str, behavior_explanations: list, core_behavioral_metrics: dict):
    """
    Executes the LLM narrative generation asynchronously to minimize request latency.

    Args:
        session_id: The unique identifier for the assessment session.
        score_id: UUID of the SessionScore record to update.
        scores_dict: Dictionary of all calculated component scores.
        excerpts: Textual context built from telemetry via build_judge_excerpt.
        behavior_explanations: SHAP feature contributions for grounding the narrative.
        core_behavioral_metrics: Raw metrics (acceptance, deliberation) for grounding.
    """
    from db import SessionLocal # Import here to avoid circular dependencies
    db = SessionLocal()
    try:
        client = GeminiClient()
        
        base_path = os.path.dirname(__file__)
        prompts_dir = os.environ.get(
            "MODEL_ARTIFACTS_DIR", 
            os.path.join(os.path.dirname(os.path.dirname(base_path)), "model", "models")
        )
        # Assuming the text files are in the 'model/prompts' directory
        model_dir = os.path.dirname(prompts_dir) if prompts_dir.endswith("models") else prompts_dir
        
        system_prompt_path = os.path.join(model_dir, "prompts", "judge_system_prompt.txt")
        user_prompt_path = os.path.join(model_dir, "prompts", "judge_user_prompt_template.txt")
        
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()
            
        with open(user_prompt_path, "r") as f:
            user_prompt_template = f.read()
            
        user_prompt = user_prompt_template.replace("{{ numerical_scores }}", json.dumps(scores_dict, indent=2))
        user_prompt = user_prompt.replace("{{ prompt_excerpts }}", excerpts)
        
        # Format SHAP explanations for the prompt
        expl_text = "\n".join([
            f"- {e['feature']}: {e['value']:.4f} (Raw) | Contribution to {scores_dict['label']}: {'+' if e['impact'] == 'increases' else ''}{e['contribution']:.4f}" 
            for e in behavior_explanations
        ])
        user_prompt = user_prompt.replace("{{ behavior_explanations }}", expl_text)
        
        # Format core metrics for grounding
        core_text = "\n".join([f"- {k.replace('_', ' ').title()}: {v:.4f}" for k, v in core_behavioral_metrics.items()])
        user_prompt = user_prompt.replace("{{ core_behavioral_metrics }}", core_text)
        
        try:
            narrative = client.judge_call(user_prompt, system_prompt)
        except Exception as api_err:
            logger.error(f"Gemini API failed during judge_call: {api_err}")
            label = scores_dict.get('label', 'Unknown').replace('_', ' ').title()
            weight = scores_dict.get('weighted', '0.0')
            narrative = f"Candidate scored {label} with a weighted score of {weight}. AI Narrative generation was bypassed due to high system load or API timeout."
        
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
