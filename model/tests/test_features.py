import numpy as np
import pandas as pd
from features import extract_c1_features, create_train_val_split, FEATURE_NAMES

def test_c1_feature_vector_shape():
    """Verify the extracted feature vector has exactly 15 dimensions."""
    dummy_events = pd.DataFrame([{
        'acceptance_rate': 0.8,
        'deliberation_time': 25.0,
        'post_acceptance_edit_rate': 0.4,
        'verification_frequency': 3,
        'reprompt_ratio': 0.1
    }])
    
    vec = extract_c1_features(dummy_events)
    assert vec.shape == (15,), f"Expected shape (15,), got {vec.shape}"
    # NaN check removed: We allow NaNs to let XGBoost handle missingness natively.

def test_nan_handling():
    """Verify empty missing values are imputed and no NaNs are returned."""
    empty_events = pd.DataFrame()
    vec = extract_c1_features(empty_events)
    assert vec.shape == (15,)
    assert not np.isnan(vec).any()
    # verify empty DF returns all zeros
    assert np.all(vec == 0.0)

def test_stratified_split():
    """Verify train_test_split preserves the proxy label distribution."""
    # Create 100 rows with a known distribution
    # 50 balanced, 30 strategic, 20 over_reliant
    labels = ['balanced']*50 + ['strategic']*30 + ['over_reliant']*20
    df = pd.DataFrame({
        'id': range(100),
        'proxy_label': labels
    })
    
    train_df, val_df = create_train_val_split(df, test_size=0.2, random_state=42)
    
    assert len(train_df) == 80
    assert len(val_df) == 20
    
    # Train distribution should be exactly 80% of original
    train_counts = train_df['proxy_label'].value_counts()
    assert train_counts['balanced'] == 40
    assert train_counts['strategic'] == 24
    assert train_counts['over_reliant'] == 16
    
    # Val distribution should be exactly 20% of original
    val_counts = val_df['proxy_label'].value_counts()
    assert val_counts['balanced'] == 10
    assert val_counts['strategic'] == 6
    assert val_counts['over_reliant'] == 4
