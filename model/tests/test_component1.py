import os
import sys
import json
import joblib
import numpy as np

from features import FEATURE_NAMES

MODELS_DIR = "model/models"
MODEL_PATH = "model/models/behavioral_classifier.joblib"
IMPORTANCES_PATH = "model/models/c1_importances.json"

def test_c1_model_loads_and_predicts():
    """Verify that the XGBoost model can be loaded and predicted upon with a 15-dim vector."""
    if not os.path.exists(MODEL_PATH):
        import pytest
        pytest.skip(f"Model artifact not found at {MODEL_PATH}. Run train_c1.py first.")
        
    model = joblib.load(MODEL_PATH)
    
    # Create a dummy feature vector of shape (1, 15)
    dummy_input = np.zeros((1, len(FEATURE_NAMES)))
    
    pred = model.predict(dummy_input)
    assert pred.shape == (1,)
    
    # Must predict one of our mapped integer classes
    assert pred[0] in [0, 1, 2]

def test_c1_importances_format():
    """Verify the importances file possesses all features and roughly sums to 1.0."""
    if not os.path.exists(IMPORTANCES_PATH):
        import pytest
        pytest.skip(f"Importances artifact not found at {IMPORTANCES_PATH}. Run train_c1.py first.")
        
    with open(IMPORTANCES_PATH, 'r') as f:
        importances = json.load(f)
        
    assert len(importances) == len(FEATURE_NAMES)
    for name in FEATURE_NAMES:
        assert name in importances
        
    total = sum(importances.values())
    import pytest
    assert total == pytest.approx(1.0, rel=0.01)
