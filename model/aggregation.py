import logging
from typing import Dict, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def aggregate_scores(
    behavioral_score: float, 
    prompt_score: float, 
    critical_score: float, 
    feature_importances: Dict[str, float] = None
) -> Tuple[float, str]:
    """Aggregates multi-modal evaluation scores into a final weighted performance metric.

    Args:
        behavioral_score: Normalized score representing structural coding behavior.
        prompt_score: Normalized score reflecting AI prompt engineering quality.
        critical_score: Normalized score measuring post-acceptance critical review.
        feature_importances: Optional mapping of feature weights used to dynamically 
            adjust component bias based on signal confidence.

    Returns:
        A tuple containing the weighted score (1.0-5.0) and the categorical label.
    """
    
    # Baseline fallback weights if no importances provided or parsing fails
    w_behavioral, w_prompt, w_critical = 0.34, 0.33, 0.33
    
    if feature_importances:
        try:
            # We attempt to derive component weights from the relative importance of their driving features
            # Behavioral scoring drives structural features
            behavioral_feats = ['deliberation_time_avg', 'verification_frequency', 'time_by_panel_editor_pct']
            
            # Prompt quality scoring drives textual evaluation. Textual features are not 
            # directly present in behavioral model importances; defaulting to baseline split.
            
            # Adjust weights when structural features from the behavioral model show high relative importance.
            behavioral_weight = sum(feature_importances.get(f, 0.0) for f in behavioral_feats)
            
            # Normalize weights to prioritize behavioral signals when they meet a high-confidence threshold.
            if behavioral_weight > 0.4:
                w_behavioral, w_prompt, w_critical = 0.50, 0.25, 0.25
            else:
                w_behavioral, w_prompt, w_critical = 0.34, 0.33, 0.33
                
        except Exception as e:
            logger.warning(f"Failed to parse feature importances for weighting, using default. {e}")
            w_behavioral, w_prompt, w_critical = 0.34, 0.33, 0.33
    
    weighted_score = (behavioral_score * w_behavioral) + (prompt_score * w_prompt) + (critical_score * w_critical)
    
    # Ensure clipping
    weighted_score = max(1.0, min(5.0, weighted_score))
    
    # Map to label
    if weighted_score >= 3.5:
        overall_label = "strategic"
    elif weighted_score >= 2.5:
        overall_label = "balanced"
    else:
        overall_label = "over_reliant"
        
    return round(float(weighted_score), 2), overall_label
