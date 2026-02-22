import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from loader import load_wildchat
from prompt_features import extract_prompt_quality_features

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# The 5 strict structural features we are using to avoid semantic over-fitting
C2_FEATURE_NAMES = [
    'prompt_length',
    'has_code_context',
    'has_function_name',
    'has_constraint_language',
    'has_scoped_verbs'
]

def parse_conversations(df: pd.DataFrame):
    """
    Parses WildChat conversations to extract pairs of:
    (current_user_prompt, next_user_prompt)
    
    We skip assistant turns because we are evaluating the user's prompt quality.
    """
    X_list = []
    y_list = []
    
    logger.info(f"Extracting C2 features from {len(df)} WildChat conversations...")
    
    for _, row in df.iterrows():
        conversation = row.get('conversation', [])
        
        # Filter for user messages only
        user_msgs = [turn['content'] for turn in conversation if turn.get('role') == 'user' and isinstance(turn.get('content'), str)]
        
        if len(user_msgs) < 2:
            continue
            
        # We look at pairs of sequential user prompts. 
        # For prompt[i], prompt[i+1] is the "next turn" used to check for re-prompt indicators.
        for i in range(len(user_msgs) - 1):
            current_prompt = user_msgs[i]
            next_prompt = user_msgs[i+1]
            
            # Extract features (which internally computes the 're_prompt_indicator' weak label)
            feats_dict = extract_prompt_quality_features(current_prompt, next_prompt)
            
            # Enforce strict structural logic
            x_vec = [feats_dict[name] for name in C2_FEATURE_NAMES]
            y_label = int(feats_dict['re_prompt_indicator'])
            
            X_list.append(x_vec)
            y_list.append(y_label)
            
    logger.info(f"Extracted {len(X_list)} prompt pairs.")
    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=int)
    
    # Simple downsampling to balance the classes if signal is rare
    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]
    
    if len(pos_idx) > 0 and len(neg_idx) > len(pos_idx):
        logger.info(f"Downsampling majority class (0) from {len(neg_idx)} to {len(pos_idx)} to balance dataset.")
        np.random.seed(config.RANDOM_SEED)
        neg_idx_sampled = np.random.choice(neg_idx, len(pos_idx), replace=False)
        balanced_idx = np.concatenate([pos_idx, neg_idx_sampled])
        np.random.shuffle(balanced_idx)
        X = X[balanced_idx]
        y = y[balanced_idx]
        
    return X, y


def train_component2():
    """Main training routine for Component 2."""
    df_raw = load_wildchat(max_records=config.WILDCHAT_MAX_RECORDS)
    
    if df_raw.empty:
        logger.error("Failed to load WildChat data. Cannot train C2.")
        return
        
    X, y = parse_conversations(df_raw)
    
    if len(X) == 0:
        logger.error("No valid prompt pairs found. Cannot train C2.")
        return
        
    logger.info("Splitting dataset...")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=config.RANDOM_SEED, stratify=y
    )
    
    logger.info(f"Training XGBoost Classifier (n={len(X_train)})...")
    model = XGBClassifier(
        n_estimators=config.C1_N_ESTIMATORS,  # Reusing existing config scale
        max_depth=config.C1_MAX_DEPTH,
        learning_rate=config.C1_LEARNING_RATE,
        random_state=config.RANDOM_SEED,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    logger.info("Evaluating on validation set...")
    y_pred = model.predict(X_val)
    acc = accuracy_score(y_val, y_pred)
    logger.info(f"Validation Accuracy: {acc:.4f}")
    
    logger.info(f"Label distribution: {pd.Series(y).value_counts(normalize=True).to_dict()}")
    
    if len(np.unique(y)) < 2:
        logger.warning("Only one class found in dataset! Cannot train a classifier. Adjusting for single-class report...")
        target_names = ["Good Prompt (0)"] if y[0] == 0 else ["Reprompt/Bad (1)"]
    else:
        target_names = ["Good Prompt (0)", "Reprompt/Bad (1)"]

    logger.info("Classification Report:\n" + classification_report(
        y_val, y_pred, target_names=target_names
    ))
    
    cm = confusion_matrix(y_val, y_pred)
    logger.info(f"Confusion Matrix:\n{cm}")
    
    baseline_acc = pd.Series(y_val).value_counts(normalize=True).max()
    logger.info(f"Majority Class Baseline: {baseline_acc:.4f}")
    
    if acc <= baseline_acc:
        logger.warning(f"Validation accuracy ({acc:.4f}) failed to beat the dummy baseline ({baseline_acc:.4f})!")
    else:
        logger.info(f"Model successfully beats minimum baseline ({baseline_acc:.4f}).")
        
    # Extract feature importances
    importances = model.feature_importances_
    # Normalize
    scale = importances.sum()
    if scale > 0:
        importances = importances / scale
        
    importance_dict = {name: float(val) for name, val in zip(C2_FEATURE_NAMES, importances)}
    
    # Save artifacts
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'prompt_quality_classifier.joblib')
    importances_path = os.path.join(models_dir, 'c2_importances.json')
    
    joblib.dump(model, model_path)
    with open(importances_path, 'w') as f:
        json.dump(importance_dict, f, indent=2)
        
    logger.info(f"Model saved to {model_path}")
    logger.info(f"Importances saved to {importances_path}")
    
    return acc

if __name__ == "__main__":
    train_component2()
