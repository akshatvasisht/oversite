import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scoring import run_behavioral_evaluation, FEATURE_NAMES

class TestSHAPIntegration(unittest.TestCase):
    @patch('services.scoring.load_models')
    @patch('services.scoring.extract_behavioral_features')
    def test_run_behavioral_evaluation_with_shap(self, mock_extract, mock_load):
        # Mock features (16 features)
        mock_features = np.random.rand(16)
        mock_extract.return_value = mock_features
        
        # Mock Calibration Wrapper
        mock_calibrator = MagicMock()
        mock_base_model = MagicMock()
        mock_base_model.feature_importances_ = np.random.rand(3)
        mock_calibrator.estimator = mock_base_model
        
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([2]) # Predicted label index for 'strategic'
        mock_model.calibrated_classifiers_ = [mock_calibrator]
        
        # Mock SHAP TreeExplainer output for 3 structural features
        mock_shap_values = [np.random.rand(1, 3) for _ in range(3)]
        
        with patch('shap.TreeExplainer') as mock_explainer_cls:
            mock_explainer = MagicMock()
            mock_explainer.shap_values.return_value = mock_shap_values
            mock_explainer_cls.return_value = mock_explainer
            
            mock_load.return_value = {'behavioral': mock_model}
            
            # Execute
            result = run_behavioral_evaluation("test-session", MagicMock())
            
            # Verify structure
            self.assertIn('explanations', result)
            self.assertEqual(len(result['explanations']), 3)
            
            for expl in result['explanations']:
                self.assertIn('feature', expl)
                self.assertIn('impact', expl)
                self.assertIn('contribution', expl)
                self.assertIn('value', expl)
                self.assertIn(expl['feature'], FEATURE_NAMES)
                # Ensure the feature is one of the structural ones (indices 12, 13, 14)
                self.assertIn(expl['feature'], [FEATURE_NAMES[12], FEATURE_NAMES[13], FEATURE_NAMES[14]])
                self.assertIn(expl['impact'], ['increases', 'decreases'])
                self.assertIsInstance(expl['contribution'], float)
                self.assertIsInstance(expl['value'], float)

if __name__ == '__main__':
    unittest.main()
