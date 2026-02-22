import logging
from typing import Dict, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def aggregate_scores(
    c1_score: float, 
    c2_score: float, 
    c3_score: float, 
    feature_importances: Dict[str, float] = None
) -> Tuple[float, str]:
    """
    Aggregates the three component scores into a final weighted score and profiling label.
    
    Args:
        c1_score (float): 1.0 - 5.0 (Structural behavior)
        c2_score (float): 1.0 - 5.0 (Prompt quality)
        c3_score (float): 1.0 - 5.0 (Critical Review / Post-acceptance edits)
        feature_importances (Dict[str, float]): The normalized feature importance mapping 
                                                from Component 1 (or combined C1/C2). 
                                                Used to dynamically weight the components.
    
    Returns:
        Tuple[float, str]: (weighted_score, overall_label)
    """
    
    # Baseline fallback weights if no importances provided or parsing fails
    w1, w2, w3 = 0.34, 0.33, 0.33
    
    if feature_importances:
        try:
            # We attempt to derive component weights from the relative importance of their driving features
            # Component 1 drives structural features
            c1_feats = ['deliberation_time_avg', 'verification_frequency', 'time_by_panel_editor_pct']
            
            # Component 2 drives textual quality (we don't get these directly in C1 importances, 
            # but we can look for proxy features if provided, otherwise assume baseline split)
            
            # If we only have C1 importances (from XGBoost), we can use the sum of its top features
            # to determine how strongly we should trust C1 over flat averages.
            c1_weight = sum(feature_importances.get(f, 0.0) for f in c1_feats)
            
            # Normalizing simplistic weights
            # For this MVP aggregation layer, if we detect strong C1 features, we bump its weight up slightly.
            if c1_weight > 0.4:
                w1, w2, w3 = 0.50, 0.25, 0.25
            else:
                w1, w2, w3 = 0.34, 0.33, 0.33
                
        except Exception as e:
            logger.warning(f"Failed to parse feature importances for weighting, using default. {e}")
            w1, w2, w3 = 0.34, 0.33, 0.33
    
    weighted_score = (c1_score * w1) + (c2_score * w2) + (c3_score * w3)
    
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
