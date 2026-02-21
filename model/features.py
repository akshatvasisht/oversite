import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.model_selection import train_test_split

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    'acceptance_rate',
    'deliberation_time_avg',
    'post_acceptance_edit_rate',
    'verification_frequency',
    'reprompt_ratio',
    'chunk_acceptance_rate',
    'passive_acceptance_rate',
    'time_on_chunk_avg_ms',
    'time_by_panel_editor_pct',
    'time_by_panel_chat_pct',
    'orientation_duration_s',
    'iteration_depth',
    'prompt_count_orientation_phase',
    'prompt_count_implementation_phase',
    'prompt_count_verification_phase'
]

def extract_c1_features(events_df: pd.DataFrame) -> np.ndarray:
    """
    Extracts 15 fixed features from raw telemetry events.
    This serves as the contract between the Backend and Model track.
    
    Args:
        events_df: A DataFrame containing a session's raw events.
                   Must contain columns matching the backend schema
                   or be pre-aggregated CUPS style dataframe.
                   
    Returns:
        np.ndarray: A 1D array of shape (15,) containing the feature values.
    """
    if events_df.empty:
        logger.warning("Empty events passed to feature extractor, returning zeros.")
        return np.zeros(len(FEATURE_NAMES))

    # Initialize a dict to hold the scalar feature values
    feats: Dict[str, float] = {k: 0.0 for k in FEATURE_NAMES}

    # IMPORTANT: The following is a mock implementation mapping a single
    # summarized row (CUPS format) to the 15 component vector. 
    # In full reality, this will parse raw `events`, `editor_events`, etc.
    # For CUPS, we extract what we can and impute the rest.

    # If it's a pre-aggregated row (like from CUPS dataloader)
    row = events_df.iloc[0] if len(events_df) > 0 else pd.Series()

    feats['acceptance_rate'] = float(row.get('acceptance_rate', 0.5))
    feats['deliberation_time_avg'] = float(row.get('deliberation_time', 10.0))
    feats['post_acceptance_edit_rate'] = float(row.get('post_acceptance_edit_rate', 0.1))
    feats['verification_frequency'] = float(row.get('verification_frequency', 0.0))
    feats['reprompt_ratio'] = float(row.get('reprompt_ratio', 0.0))
    
    # Impute missing values for backend-specific granular features not in CUPS.
    # We use neutral/median defaults so training doesn't break, and the model
    # learns to rely on the primary CUPS features.
    feats['chunk_acceptance_rate'] = float(row.get('chunk_acceptance_rate', feats['acceptance_rate']))
    feats['passive_acceptance_rate'] = float(row.get('passive_acceptance_rate', 0.2))
    feats['time_on_chunk_avg_ms'] = float(row.get('time_on_chunk_avg_ms', 5000.0))
    feats['time_by_panel_editor_pct'] = float(row.get('time_by_panel_editor_pct', 0.6))
    feats['time_by_panel_chat_pct'] = float(row.get('time_by_panel_chat_pct', 0.4))
    feats['orientation_duration_s'] = float(row.get('orientation_duration_s', 30.0))
    feats['iteration_depth'] = float(row.get('iteration_depth', 1.0))
    feats['prompt_count_orientation_phase'] = float(row.get('prompt_count_orientation_phase', 1.0))
    feats['prompt_count_implementation_phase'] = float(row.get('prompt_count_implementation_phase', 3.0))
    feats['prompt_count_verification_phase'] = float(row.get('prompt_count_verification_phase', 1.0))

    # Return exactly the 15 features in established order
    vector = np.array([feats[name] for name in FEATURE_NAMES], dtype=np.float32)
    
    # NaN check fallback
    vector = np.nan_to_num(vector, nan=0.0)
    
    return vector

def create_train_val_split(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> tuple:
    """
    Creates a stratified train/validation split preserving the proxy label distribution.
    
    Args:
        df: The dataset containing features and a 'proxy_label' column.
        test_size: Proportion of dataset for validation.
        random_state: Seed for reproducibility.
        
    Returns:
        tuple: (train_df, val_df)
    """
    if 'proxy_label' not in df.columns:
        raise ValueError("DataFrame must contain 'proxy_label' column for stratified splitting.")
        
    logger.info(f"Splitting dataset of {len(df)} records (stratified by proxy_label)...")
    
    train_df, val_df = train_test_split(
        df, 
        test_size=test_size, 
        random_state=random_state, 
        stratify=df['proxy_label']
    )
    
    logger.info(f"Split complete: {len(train_df)} train, {len(val_df)} validation.")
    return train_df, val_df
