import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from features import extract_behavioral_features, create_train_val_split, FEATURE_NAMES

def test_c1_feature_vector_shape():
    """Verify the extracted feature vector has exactly 16 dimensions."""
    telemetry = {
        'decisions': [],
        'events': [],
        'interactions': [],
        'session_start': datetime.now()
    }
    
    vec = extract_behavioral_features(telemetry)
    assert vec.shape == (16,), f"Expected shape (16,), got {vec.shape}"

def test_nan_handling():
    """Verify empty telemetry returns all zeros and no NaNs."""
    telemetry = {
        'decisions': [],
        'events': [],
        'interactions': [],
        'session_start': None
    }
    vec = extract_behavioral_features(telemetry)
    assert vec.shape == (16,)
    assert not np.isnan(vec).any()
    assert np.all(vec == 0.0)

def test_prompt_normalization():
    """Verify prompt counts are normalized by total count."""
    telemetry = {
        'decisions': [],
        'events': [],
        'interactions': [
            {'phase': 'orientation'},
            {'phase': 'implementation'},
            {'phase': 'implementation'},
            {'phase': 'verification'}
        ],
        'session_start': None
    }
    vec = extract_behavioral_features(telemetry)
    # Total prompts = 4
    # orientation = 1/4 = 0.25
    # implementation = 2/4 = 0.5
    # verification = 1/4 = 0.25
    assert vec[12] == 0.25 # count_prompt_orientation
    assert vec[13] == 0.5  # count_prompt_implementation
    assert vec[14] == 0.25 # count_prompt_verification

def test_deliberation_to_action_ratio():
    """Verify deliberation_to_action_ratio calculation."""
    telemetry = {
        'decisions': [
            {'decision': 'modified', 'time_on_chunk_ms': 1000, 'proposed_code': 'a', 'final_code': 'abc'}, # edit_rate = 2/1 = 2.0
            {'decision': 'modified', 'time_on_chunk_ms': 2000, 'proposed_code': 'x', 'final_code': 'xyz'} # edit_rate = 2/1 = 2.0
        ],
        'events': [],
        'interactions': [],
        'session_start': None
    }
    vec = extract_behavioral_features(telemetry)
    # avg_deliberation = (1000 + 2000) / 2 = 1500
    # avg_edit_rate = (2.0 + 2.0) / 2 = 2.0
    # ratio = 1500 / 2.0 = 750.0
    assert vec[1] == 1500.0
    assert vec[2] == 2.0
    assert vec[15] == 750.0

def test_stratified_split():
    """Verify train_test_split preserves the proxy label distribution."""
    labels = ['balanced']*50 + ['strategic']*30 + ['over_reliant']*20
    df = pd.DataFrame({
        'id': range(100),
        'proxy_label': labels
    })
    
    train_df, val_df = create_train_val_split(df, test_size=0.2, random_state=42)
    
    assert len(train_df) == 80
    assert len(val_df) == 20
    
    train_counts = train_df['proxy_label'].value_counts()
    assert train_counts['balanced'] == 40
    assert train_counts['strategic'] == 24
    assert train_counts['over_reliant'] == 16
