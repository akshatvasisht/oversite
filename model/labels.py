import logging
import pandas as pd
from loader import load_cups
from config import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def apply_proxy_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns behavior labels (strategic, over_reliant, balanced) based on telemetry heuristics.
    
    Strategic: Low blind acceptance, high pause/deliberation, high post-edit rates.
    Over-reliant: High blind acceptance, low pause/deliberation, low post-edit rates.
    Balanced: Median behavior.
    
    Args:
        df: CUPS telemetry DataFrame.
        
    Returns:
        pd.DataFrame: DataFrame with an additional 'proxy_label' column.
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to labeling logic.")
        return df

    logger.info("Computing quantile thresholds for proxy labeling...")
    
    # Pre-calculate thresholds based on config quantiles
    thresholds = {
        'acc': {
            'low': df['rate_acceptance'].quantile(config.LOW_THRESHOLD),
            'high': df['rate_acceptance'].quantile(config.HIGH_THRESHOLD)
        },
        'delib': {
            'low': df['duration_deliberation_avg'].quantile(config.LOW_THRESHOLD),
            'high': df['duration_deliberation_avg'].quantile(config.HIGH_THRESHOLD)
        },
        'edit': {
            'low': df['rate_post_acceptance_edit'].quantile(config.LOW_THRESHOLD),
            'high': df['rate_post_acceptance_edit'].quantile(config.HIGH_THRESHOLD)
        }
    }

    def determine_label(row: pd.Series) -> str:
        score = 0
        
        # Lower acceptance rate -> Strategic behavior
        if pd.notna(row['rate_acceptance']):
            if row['rate_acceptance'] <= thresholds['acc']['low']:
                score += 1
            elif row['rate_acceptance'] > thresholds['acc']['high']:
                score -= 1
                
        # Higher deliberation time -> Strategic behavior
        if pd.notna(row['duration_deliberation_avg']):
            if row['duration_deliberation_avg'] >= thresholds['delib']['high']:
                score += 1
            elif row['duration_deliberation_avg'] < thresholds['delib']['low']:
                score -= 1
                
        # Higher edit rate post-acceptance -> Strategic behavior
        if pd.notna(row['rate_post_acceptance_edit']):
            if row['rate_post_acceptance_edit'] >= thresholds['edit']['high']:
                score += 1
            elif row['rate_post_acceptance_edit'] < thresholds['edit']['low']:
                score -= 1
                
        if score >= 1:
            return 'strategic'
        elif score <= -1:
            return 'over_reliant'
        else:
            return 'balanced'

    logger.info("Applying labeling heuristics...")
    df['proxy_label'] = df.apply(determine_label, axis=1)
    
    label_counts = df['proxy_label'].value_counts()
    logger.info(f"Label distribution:\n{label_counts}")
    return df

if __name__ == "__main__":
    df = load_cups()
    labeled_df = apply_proxy_labels(df)
