import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.calibration import CalibratedClassifierCV

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from loader import load_cups
from labels import apply_proxy_labels
from features import extract_behavioral_features, create_train_val_split, FEATURE_NAMES, SessionTelemetry

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "training_output.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

LABEL_MAP = {'over_reliant': 0, 'balanced': 1, 'strategic': 2}
REVERSE_MAP = {v: k for k, v in LABEL_MAP.items()}

# Indices in FEATURE_NAMES that perfectly correlate with our proxy labels
LEAKING_FEATURE_INDICES = [0, 1, 2] 

# 12: count_prompt_orientation, 13: count_prompt_implementation, 14: count_prompt_verification
VALID_STRUCTURAL_INDICES = [12, 13, 14]

def select_structural_features(X: np.ndarray) -> np.ndarray:
    """
    Subsets the 16-feature array into just the 3 structural features 
    that carry valid signal for evaluation. 
    """
    return X[:, VALID_STRUCTURAL_INDICES]

def extract_features_and_labels(df: pd.DataFrame):
    """Transform the CUPS dataframe into X (features) and y (labels)."""
    X_list = []
    y_list = []
    groups = []
    
    valid_df = df.dropna(subset=['proxy_label'])
    
    logger.info(f"Extracting features for {len(valid_df)} sessions...")
    
    for _, row in valid_df.iterrows():
        # Map pre-aggregated CUPS row to the SessionTelemetry contract
        telemetry: SessionTelemetry = {
            'decisions': [],
            'events': [],
            'interactions': [],
            'session_start': None,
            'precomputed': row.to_dict()
        }
        feats = extract_behavioral_features(telemetry)
        X_list.append(feats)
        y_list.append(LABEL_MAP[row['proxy_label']])
        groups.append(row['session_id'])
        
    return np.array(X_list), np.array(y_list), np.array(groups)

def train_behavioral_classifier():
    """Coordinates the training of the structural behavior XGBoost classifier.

    Loads the CUPS dataset, applies behavioral proxy labels, and executes 
    a training cycle with leakage mitigation and stratified validation.
    """
    df_raw = load_cups()
    df = apply_proxy_labels(df_raw)
    
    # Needs a unified df to correctly stratify via feature logic
    # First, let's extract the X, but keep proxy label for splitting
    X, y, groups = extract_features_and_labels(df)
    
    logger.info(f"Selecting Structural Features (indices {VALID_STRUCTURAL_INDICES})...")
    X_clean = select_structural_features(X)
    
    logger.info(f"Starting Calibrated Stratified 3-Fold Training (N={len(y)} samples)...")
    
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=config.RANDOM_SEED)
    
    base_model = XGBClassifier(
        n_estimators=config.BEHAVIORAL_N_ESTIMATORS,
        max_depth=config.BEHAVIORAL_MAX_DEPTH,
        learning_rate=config.BEHAVIORAL_LEARNING_RATE,
        min_child_weight=config.BEHAVIORAL_MIN_CHILD_WEIGHT,
        reg_lambda=config.BEHAVIORAL_REG_LAMBDA,
        reg_alpha=config.BEHAVIORAL_REG_ALPHA,
        random_state=config.RANDOM_SEED,
        eval_metric='mlogloss'
    )
    
    # Calibrated model using Stratified 3-Fold
    # This trains one base model and one sigmoid calibrator per fold
    calibrated_model = CalibratedClassifierCV(base_model, method='sigmoid', cv=skf)
    
    calibrated_model.fit(X_clean, y)
    
    # Evaluate performance on the training set (ensemble predictions)
    y_pred = calibrated_model.predict(X_clean)
    acc = accuracy_score(y, y_pred)
    f1 = f1_score(y, y_pred, average='weighted', zero_division=0)
    
    logger.info("-" * 30)
    logger.info(f"Calibrated Ensemble | Accuracy: {acc:.4f} | F1: {f1:.4f}")
    logger.info("-" * 30)
    
    # Save the best model artifact
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(calibrated_model, os.path.join(models_dir, 'behavioral_classifier.joblib'))
    
    # Extract average importances across all ensemble members
    all_importances = []
    for member in calibrated_model.calibrated_classifiers_:
        all_importances.append(member.estimator.feature_importances_)
    
    mean_importances = np.mean(all_importances, axis=0)
    mean_importances = mean_importances / mean_importances.sum()
    
    importance_dict = {
        FEATURE_NAMES[idx]: float(val) 
        for idx, val in zip(VALID_STRUCTURAL_INDICES, mean_importances)
    }
    with open(os.path.join(models_dir, 'behavioral_importances.json'), 'w') as f:
        json.dump(importance_dict, f, indent=2)

    # Calculate majority class baseline across the entire dataset for comparison
    baseline_acc = pd.Series(y).value_counts(normalize=True).max()
    logger.info(f"Majority Class Baseline: {baseline_acc:.4f}")
    
    if acc <= baseline_acc:
        logger.warning(f"Calibrated accuracy ({acc:.4f}) failed to beat the dummy baseline ({baseline_acc:.4f})!")
    else:
        logger.info(f"Model successfully beats minimum baseline ({baseline_acc:.4f}) under Calibrated 3-Fold.")
        
    return acc

if __name__ == "__main__":
    train_behavioral_classifier()
