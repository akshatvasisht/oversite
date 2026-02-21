import logging
import pandas as pd
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loader import load_cups
from config import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_eda_plots(df: pd.DataFrame) -> None:
    """
    Generates and saves exploratory data analysis plots from the telemetry DataFrame.
    
    Plots include distributions for acceptance rate, deliberation time, 
    and post-acceptance edit rate.
    
    Args:
        df: The DataFrame containing CUPS telemetry.
    """
    if df.empty:
        logger.warning("Dataframe is empty, skipping EDA.")
        return

    sns.set_theme(style="whitegrid")
    metrics = [
        ('acceptance_rate', 'Acceptance Rate', 'acceptance_rate_dist.png'),
        ('deliberation_time', 'Deliberation Time (Seconds)', 'deliberation_time_dist.png'),
        ('post_acceptance_edit_rate', 'Post-Acceptance Edit Rate', 'post_acceptance_edit_rate_dist.png')
    ]

    for col, label, filename in metrics:
        if col in df.columns:
            logger.info(f"Generating distribution plot for {col}...")
            plt.figure(figsize=(8, 5))
            sns.histplot(df[col], bins=30, kde=True)
            plt.title(f'Distribution of {label}')
            plt.xlabel(label)
            plt.ylabel('Frequency')
            plt.savefig(f"{config.EDA_DIR}/{filename}")
            plt.close()
            logger.info(f"Saved plot to {config.EDA_DIR}/{filename}")
        else:
            logger.warning(f"Metric {col} not found in DataFrame.")

if __name__ == "__main__":
    df = load_cups()
    generate_eda_plots(df)
