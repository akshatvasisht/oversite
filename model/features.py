import logging
import numpy as np
import pandas as pd
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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

def compute_c1_features(
    decisions: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    interactions: List[Dict[str, Any]],
    session_start: Optional[datetime] = None
) -> np.ndarray:
    """
    Computes 15 features from raw session data.
    This is the core logic shared between Backend (Serving) and Model (Training/Eval).
    """
    feats: Dict[str, float] = {name: 0.0 for name in FEATURE_NAMES}
    
    # 1. Chunk decisions metrics
    total_chunks = len(decisions)
    if total_chunks > 0:
        accepted = [d for d in decisions if d.get('decision') == 'accepted']
        modified = [d for d in decisions if d.get('decision') == 'modified']
        
        feats['rate_acceptance'] = len(accepted) / total_chunks
        feats['rate_chunk_acceptance'] = (len(accepted) + len(modified)) / total_chunks
        feats['rate_passive_acceptance'] = len(accepted) / total_chunks
        
        times = [d.get('time_on_chunk_ms') for d in decisions if d.get('time_on_chunk_ms')]
        if times:
            avg_time = sum(times) / len(times)
            feats['duration_deliberation_avg'] = avg_time
            feats['duration_chunk_avg_ms'] = avg_time
            
        edit_rates = []
        for d in modified:
            proposed = d.get('proposed_code', '')
            final = d.get('final_code', '')
            if proposed and final:
                change = abs(len(final) - len(proposed)) / max(1, len(proposed))
                edit_rates.append(change)
        if edit_rates:
            feats['rate_post_acceptance_edit'] = sum(edit_rates) / len(edit_rates)

    # 2. Event based metrics
    total_events = len(events)
    if total_events > 0:
        exec_count = len([e for e in events if e.get('event_type') == 'execute'])
        feats['freq_verification'] = exec_count / total_events
        
        panel_events = [e for e in events if e.get('event_type') == 'panel_focus']
        if panel_events:
            editor_count = len([e for e in panel_events if e.get('content') == 'editor'])
            chat_count = len([e for e in panel_events if e.get('content') == 'chat'])
            total_panel = len(panel_events)
            feats['pct_time_editor'] = editor_count / total_panel
            feats['pct_time_chat'] = chat_count / total_panel
            
        # Orientation Duration
        # Sort events by timestamp if not already sorted
        sorted_events = sorted(events, key=lambda x: x.get('timestamp') if x.get('timestamp') else datetime.min)
        first_action = next((e for e in sorted_events if e.get('event_type') in ['edit', 'prompt']), None)
        
        if first_action and session_start:
            # Handle both datetime and string timestamps if needed
            fa_ts = first_action.get('timestamp')
            if isinstance(fa_ts, str):
                try: fa_ts = datetime.fromisoformat(fa_ts)
                except: fa_ts = None
            
            if fa_ts:
                dur = (fa_ts - session_start).total_seconds()
                feats['duration_orientation_s'] = max(0.0, dur)
            
        # Iteration Depth
        cycles = 0
        last_was_edit = False
        for e in sorted_events:
            if e.get('event_type') == 'edit':
                last_was_edit = True
            elif e.get('event_type') == 'execute' and last_was_edit:
                cycles += 1
                last_was_edit = False
        feats['depth_iteration'] = float(cycles)

    # 3. Interaction/Phase based metrics
    if interactions:
        feats['count_prompt_orientation'] = len([p for p in interactions if p.get('phase') == 'orientation'])
        feats['count_prompt_implementation'] = len([p for p in interactions if p.get('phase') == 'implementation'])
        feats['count_prompt_verification'] = len([p for p in interactions if p.get('phase') == 'verification'])
        
        # Reprompt ratio
        sorted_prompts = sorted(interactions, key=lambda x: x.get('shown_at') if x.get('shown_at') else datetime.min)
        reprompts = 0
        for i in range(1, len(sorted_prompts)):
            prev_ts = sorted_prompts[i-1].get('shown_at')
            curr_ts = sorted_prompts[i].get('shown_at')
            if isinstance(prev_ts, str): prev_ts = datetime.fromisoformat(prev_ts)
            if isinstance(curr_ts, str): curr_ts = datetime.fromisoformat(curr_ts)
            
            if prev_ts and curr_ts and (curr_ts - prev_ts).total_seconds() < 60:
                reprompts += 1
        feats['ratio_reprompt'] = reprompts / len(interactions)

    return np.array([feats[name] for name in FEATURE_NAMES], dtype=np.float32)

def extract_behavioral_features(data: Any) -> np.ndarray:
    """
    Polymorphic extractor for Component 1 features.
    Supports:
    - pd.DataFrame (legacy CUPS aggregation)
    - Dict with 'decisions', 'events', 'interactions', 'session_start' (serving/raw)
    """
    if isinstance(data, pd.DataFrame):
        # Legacy CUPS logic for training
        if data.empty:
            return np.zeros(len(FEATURE_NAMES))
        row = data.iloc[0]
        feats = {name: float(row.get(name, np.nan)) for name in FEATURE_NAMES}
        # Backward compat for CUPS field names if they differ
        if 'deliberation_time' in row: feats['duration_deliberation_avg'] = float(row['deliberation_time'])
        
        return np.array([feats[name] for name in FEATURE_NAMES], dtype=np.float32)
    
    if isinstance(data, dict):
        return compute_c1_features(
            decisions=data.get('decisions', []),
            events=data.get('events', []),
            interactions=data.get('interactions', []),
            session_start=data.get('session_start')
        )

    logger.error(f"Unsupported data type passed to extract_behavioral_features: {type(data)}")
    return np.zeros(len(FEATURE_NAMES))

def create_train_val_split(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> tuple:
    if 'proxy_label' not in df.columns:
        raise ValueError("DataFrame must contain 'proxy_label' column for stratified splitting.")
        
    train_df, val_df = train_test_split(
        df, 
        test_size=test_size, 
        random_state=random_state, 
        stratify=df['proxy_label']
    )
    return train_df, val_df
