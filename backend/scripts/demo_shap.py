import os
import sys
import numpy as np
import json
import logging
from unittest.mock import MagicMock, patch

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "demo_output.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scoring import run_behavioral_evaluation, FEATURE_NAMES

def demo_shap_output():
    logger.info("--- SHAP EXPLANATION DEMO ---")
    
    # Mock features (full 16-feature contract)
    # 0: rate_acceptance, 1: duration_deliberation_avg, 2: rate_post_acceptance_edit
    # 3: freq_verification, 4: ratio_reprompt, 12: count_prompt_orientation, 13: count_prompt_implementation, 14: count_prompt_verification
    mock_features = np.zeros(len(FEATURE_NAMES))
    mock_features[0] = 0.5   # rate_acceptance
    mock_features[1] = 5000.0 # duration_deliberation_avg
    mock_features[2] = 0.2   # rate_post_acceptance_edit
    mock_features[3] = 0.8   # freq_verification (High)
    mock_features[12] = 4.0  # orientation_prompts
    
    # Mock model (expects only 5 features)
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([2]) # Predicted index for 'strategic'
    
    # Mock SHAP values (strategic class index 2) for the 3 structural features
    mock_shap_per_class = [np.zeros((1, 3)) for _ in range(3)]
    # Features that pushed TO strategic (Indices within the 3-subset)
    # Subset: [12, 13, 14] -> 0: count_prompt_orientation
    mock_shap_per_class[2][0, 0] = 0.25 # high orientation pushed UP prob
    
    with patch('services.scoring.load_models') as mock_load:
        with patch('services.scoring.extract_behavioral_features') as mock_extract:
            with patch('shap.TreeExplainer') as mock_explainer_cls:
                mock_load.return_value = {'behavioral': mock_model}
                mock_extract.return_value = mock_features
                
                mock_explainer = MagicMock()
                mock_explainer.shap_values.return_value = mock_shap_per_class
                mock_explainer_cls.return_value = mock_explainer
                
                result = run_behavioral_evaluation("demo-session", MagicMock())
                
                logger.info(f"Predicted Label: {result['label']}")
                logger.info(f"Calculated Score: {result['score']}")
                
                logger.info("Core Behavioral Metrics (Raw for Grounding):")
                logger.info("-" * 40)
                for k, v in result['core_metrics'].items():
                    logger.info(f"- {k}: {v}")

                logger.info("Structural Model Explanations (SHAP on non-leaking subset):")
                logger.info("-" * 40)
                for i, expl in enumerate(result['explanations']):
                    logger.info(f"{i+1}. {expl['feature']}")
                    logger.info(f"   Value: {expl['value']}")
                    logger.info(f"   Impact: {expl['impact']} probability of {result['label']}")
                    logger.info(f"   Contribution Magnitude: {expl['contribution']:.4f}")

if __name__ == "__main__":
    demo_shap_output()
