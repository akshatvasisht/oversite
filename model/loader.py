import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datasets import load_dataset
from config import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def load_cups() -> pd.DataFrame:
    """
    Loads the CUPS dataset from HuggingFace.
    
    If the dataset is unavailable, generates a synthetic dataset to ensure 
    downstream EDA components remain functional.
    
    Returns:
        pd.DataFrame: A DataFrame containing programming session telemetry.
    """
    logger.info(f"Attempting to load CUPS dataset: {config.CUPS_DATASET}")
    try:
        ds = load_dataset(config.CUPS_DATASET, split='train')
        df = ds.to_pandas()
        logger.info("Successfully loaded CUPS dataset.")
        return df
    except Exception as e:
        logger.warning(f"Failed to load CUPS dataset: {e}. Generating localized mock data to maintain development flow.")
        np.random.seed(config.RANDOM_SEED)
        n = 1000
        return pd.DataFrame({
            'session_id': [f's_{i}' for i in range(n)],
            'acceptance_rate': np.random.beta(2, 5, n),
            'deliberation_time': np.random.exponential(15, n),
            'post_acceptance_edit_rate': np.random.beta(1, 4, n),
            'verification_frequency': np.random.poisson(2, n),
            'reprompt_ratio': np.random.uniform(0, 0.5, n),
        })

def passes_wildchat_filters(conversation: List[Dict[str, Any]]) -> bool:
    """
    Determines if a WildChat conversation meets the coding session criteria.
    
    Criteria:
    - At least config.WILDCHAT_MIN_TURNS turns.
    - Contains at least one markdown code block (```).
    
    Args:
        conversation: A list of message turn dictionaries.
        
    Returns:
        bool: True if the conversation passes the filters.
    """
    if not isinstance(conversation, list) or len(conversation) < config.WILDCHAT_MIN_TURNS:
        return False
    
    return any(
        isinstance(turn.get('content', ''), str) and '```' in turn['content'] 
        for turn in conversation
    )

def load_wildchat(max_records: int = config.WILDCHAT_MAX_RECORDS) -> pd.DataFrame:
    """
    Loads and filters the WildChat dataset using streaming.
    
    Args:
        max_records: Maximum number of filtered records to collect.
        
    Returns:
        pd.DataFrame: A DataFrame of filtered coding conversations.
    """
    logger.info(f"Streaming WildChat dataset: {config.WILDCHAT_DATASET}")
    try:
        ds = load_dataset(config.WILDCHAT_DATASET, split='train', streaming=True)
        records: List[Dict[str, Any]] = []
        for row in ds:
            if passes_wildchat_filters(row.get('conversation', [])):
                records.append(row)
                if len(records) >= max_records:
                    break
        df = pd.DataFrame(records)
        logger.info(f"Collected {len(df)} WildChat coding records.")
        return df
    except Exception as e:
        logger.error(f"Error loading WildChat: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    cups_df = load_cups()
    wc_df = load_wildchat(100)
    logger.info(f"CUPS loaded: {len(cups_df)} records")
    logger.info(f"Wildchat loaded: {len(wc_df)} records")
