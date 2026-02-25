import os
import sys
import json
import joblib
import numpy as np

from features import FEATURE_NAMES

MODELS_DIR = "model/models"
MODEL_PATH = "model/models/behavioral_classifier.joblib"
IMPORTANCES_PATH = "model/models/behavioral_importances.json"

# structural_indices = [12, 13, 14]
VALID_STRUCTURAL_INDICES = [12, 13, 14]

def test_behavioral_model_loads_and_predicts():
    """Verify that the XGBoost model can be loaded and predicted upon with a 16-dim vector."""
    if not os.path.exists(MODEL_PATH):
        import pytest
        pytest.skip(f"Model artifact not found at {MODEL_PATH}. Run train_c1.py first.")
        
    model = joblib.load(MODEL_PATH)
    
    # Create a dummy feature vector of shape (1, 16) and slice to structural
    dummy_input = np.zeros((1, len(FEATURE_NAMES)))
    X_structural = dummy_input[:, VALID_STRUCTURAL_INDICES]
    
    pred = model.predict(X_structural)
    assert pred.shape == (1,)
    
    # Must predict one of our mapped integer classes
    assert pred[0] in [0, 1, 2]

def test_behavioral_importances_format():
    """Verify the importances file possesses all features and roughly sums to 1.0."""
    if not os.path.exists(IMPORTANCES_PATH):
        import pytest
        pytest.skip(f"Importances artifact not found at {IMPORTANCES_PATH}. Run train_c1.py first.")
        
    with open(IMPORTANCES_PATH, 'r') as f:
        importances = json.load(f)
        
    # Now contains ONLY the structural features [12, 13, 14]
    assert len(importances) == 3
    for idx in VALID_STRUCTURAL_INDICES:
        assert FEATURE_NAMES[idx] in importances
        
    total = sum(importances.values())
    import pytest
    assert total == pytest.approx(1.0, rel=0.01)
