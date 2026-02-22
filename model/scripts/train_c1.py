import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from loader import load_cups
from labels import apply_proxy_labels
from features import extract_behavioral_features, create_train_val_split, FEATURE_NAMES

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LABEL_MAP = {'over_reliant': 0, 'balanced': 1, 'strategic': 2}
REVERSE_MAP = {v: k for k, v in LABEL_MAP.items()}

# Indices in FEATURE_NAMES that perfectly correlate with our proxy labels
LEAKING_FEATURE_INDICES = [0, 1, 2] 

def remove_target_leakage(X: np.ndarray) -> np.ndarray:
    """
    Zeroes out the columns that were used to generate the proxy labels.
    This prevents the model from achieving artificially high accuracy by simply 
    reverse-engineering our proxy generation logic, forcing it to learn 
    from the remaining 12 secondary structural features.
    """
    X_clean = X.copy()
    for idx in LEAKING_FEATURE_INDICES:
        X_clean[:, idx] = 0.0
    return X_clean

def extract_features_and_labels(df: pd.DataFrame):
    """Transform the CUPS dataframe into X (features) and y (labels)."""
    X_list = []
    y_list = []
    
    valid_df = df.dropna(subset=['proxy_label'])
    
    logger.info(f"Extracting features for {len(valid_df)} sessions...")
    
    for _, row in valid_df.iterrows():
        # extract_behavioral_features expects a dataframe
        row_df = pd.DataFrame([row])
        feats = extract_behavioral_features(row_df)
        X_list.append(feats)
        y_list.append(LABEL_MAP[row['proxy_label']])
        
    return np.array(X_list), np.array(y_list)

def train_component1():
    """Main training routine for Component 1."""
    df_raw = load_cups()
    df = apply_proxy_labels(df_raw)
    
    # Needs a unified df to correctly stratify via feature logic
    # First, let's extract the X, but keep proxy label for splitting
    X, y = extract_features_and_labels(df)
    
    logger.info("Mitigating Target Leakage...")
    X_clean = remove_target_leakage(X)
    
    logger.info("Splitting dataset...")
    # Scikit-learn directly handles numpy arrays for splitting
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(
        X_clean, y, test_size=0.2, random_state=config.RANDOM_SEED, stratify=y
    )
    
    logger.info(f"Training XGBoost Classifier (n={len(X_train)})...")
    model = XGBClassifier(
        n_estimators=config.C1_N_ESTIMATORS,
        max_depth=config.C1_MAX_DEPTH,
        learning_rate=config.C1_LEARNING_RATE,
        random_state=config.RANDOM_SEED,
        eval_metric='mlogloss'
    )
    
    model.fit(X_train, y_train)
    
    logger.info("Evaluating on validation set...")
    y_pred = model.predict(X_val)
    acc = accuracy_score(y_val, y_pred)
    logger.info(f"Validation Accuracy: {acc:.4f}")
    
    logger.info("Classification Report:\n" + classification_report(
        y_val, y_pred, target_names=["over_reliant", "balanced", "strategic"]
    ))
    
    cm = confusion_matrix(y_val, y_pred)
    logger.info(f"Confusion Matrix:\n{cm}")

    
    # Calculate majority class baseline
    baseline_acc = pd.Series(y_val).value_counts(normalize=True).max()
    logger.info(f"Majority Class Baseline: {baseline_acc:.4f}")
    
    if acc <= baseline_acc:
        logger.warning(f"Validation accuracy ({acc:.4f}) failed to beat the dummy baseline ({baseline_acc:.4f})!")
    else:
        logger.info(f"Model successfully beats minimum baseline ({baseline_acc:.4f}), which is expected for decoupled synthetic data.")
        
    # Extract feature importances
    importances = model.feature_importances_
    # Normalize just in case, though XGBoost usually normalizes
    importances = importances / importances.sum()
    
    importance_dict = {name: float(val) for name, val in zip(FEATURE_NAMES, importances)}
    
    # Save artifacts
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'behavioral_classifier.joblib')
    importances_path = os.path.join(models_dir, 'c1_importances.json')
    
    joblib.dump(model, model_path)
    with open(importances_path, 'w') as f:
        json.dump(importance_dict, f, indent=2)
        
    logger.info(f"Model saved to {model_path}")
    logger.info(f"Importances saved to {importances_path}")
    
    return acc

if __name__ == "__main__":
    train_component1()
