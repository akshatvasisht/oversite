import logging
import os
import urllib.request
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datasets import load_dataset
from config import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def load_cups(force_download: bool = False) -> pd.DataFrame:
    """Loads and normalizes the CUPS dataset for behavioral modeling.

    Retrieves aggregated programming session telemetry records from the 
    official Microsoft repository and performs feature projection to align 
    with the 15-feature behavioral contract.

    Args:
        force_download: If true, bypasses local cache and re-downloads the dataset.

    Returns:
        pd.DataFrame: A normalized dataset of session evaluation records.
    """
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    pkl_path = os.path.join(data_dir, 'data_labeled_study.pkl')
    
    if force_download or not os.path.exists(pkl_path):
        url = "https://raw.githubusercontent.com/microsoft/coderec_programming_states/main/data/data_labeled_study.pkl"
        logger.info(f"Downloading real CUPS dataset from {url}...")
        try:
            import urllib.request
            urllib.request.urlretrieve(url, pkl_path)
            logger.info("Download complete.")
        except Exception as e:
            logger.error(f"Failed to download CUPS dataset: {e}")
            raise RuntimeError("Cannot proceed without the real CUPS dataset as requested.")
    else:
        logger.info(f"Using cached CUPS dataset at {pkl_path}")
        
    try:
        # The pickle file contains a list of 21 DataFrames (one per user)
        user_dfs = pd.read_pickle(pkl_path)
        logger.info(f"Loaded records for {len(user_dfs)} users.")
        
        aggregated_rows = []
        for df in user_dfs:
            if df.empty:
                continue
                
            user_id = df['UserId'].iloc[0]
            
            # 1. Acceptance Rate: 'Accepted' vs 'Shown'
            shown_count = (df['StateName'] == 'Shown').sum()
            accepted_count = (df['StateName'] == 'Accepted').sum()
            acc_rate = accepted_count / shown_count if shown_count > 0 else 0.0
            
            # 2. Deliberation Time: Time spent in 'Shown' state before 'Accepted' or 'Rejected'
            # We approximate this by looking at TimeSpentInState where StateName == 'Shown'
            delib_time = df[df['StateName'] == 'Shown']['TimeSpentInState'].mean()
            if pd.isna(delib_time):
                delib_time = 0.0
                
            # 3. Verification Frequency: How often they enter 'Thinking/Verifying Suggestion (A)'
            verif_freq = (df['LabeledState'] == 'Thinking/Verifying Suggestion (A)').sum()
            
            # 4. Post-Acceptance Edit Rate:
            # We use 'Editing Last Suggestion (X)' state prevalence
            edit_sugg_count = (df['LabeledState'] == 'Editing Last Suggestion (X)').sum()
            edit_rate = edit_sugg_count / accepted_count if accepted_count > 0 else 0.0
            
            # 5. Reprompt Ratio:
            prompt_count = (df['LabeledState'] == 'Prompt Crafting (V)').sum()
            reprompt_ratio = prompt_count / len(df) if len(df) > 0 else 0.0
            
            # 6. Orientation Phase Prompt Count
            orient_count = (df['LabeledState'] == 'Looking up Documentation (N)').sum()

            # 7. Functional Implementation
            impl_count = (df['LabeledState'] == 'Writing New Functionality (Z)').sum()
            
            # 8. Engagement Depth (Thinking + Debugging)
            depth_count = (df['LabeledState'] == 'Thinking About New Code To Write (F)').sum() + \
                          (df['LabeledState'] == 'Debugging/Testing Code (H)').sum()
            
            # 9. Manual Code Editing
            manual_edit_count = (df['LabeledState'] == 'Editing Written Code(C)').sum()
            edit_ratio = manual_edit_count / len(df) if len(df) > 0 else 0.0

            row = {
                'session_id': str(user_id),
                'rate_acceptance': acc_rate,
                'duration_deliberation_avg': delib_time,
                'rate_post_acceptance_edit': edit_rate,
                'freq_verification': verif_freq,
                'ratio_reprompt': reprompt_ratio,
                'count_prompt_orientation': orient_count,
                'count_prompt_implementation': impl_count,
                'count_prompt_verification': verif_freq * 0.5,
                'duration_orientation_s': orient_count * 15.0, # Proxy: 15s per documentation action
                'depth_iteration': float(depth_count),
                'pct_time_chat': reprompt_ratio,
                'pct_time_editor': edit_ratio
            }
            aggregated_rows.append(row)
            
        final_df = pd.DataFrame(aggregated_rows)
        logger.info(f"Aggregated into {len(final_df)} session records.")
        return final_df
        
    except Exception as e:
        logger.error(f"Error parsing CUPS data: {e}")
        raise

def passes_wildchat_filters(conversation: List[Dict[str, Any]]) -> bool:
    """Evaluates if a WildChat conversation satisfies coding session heuristics.

    Filters for multi-turn interactions containing explicit markdown code blocks.
    """
    if len(conversation) < config.WILDCHAT_MIN_TURNS:
        return False
    
    return any(
        isinstance(turn.get('content', ''), str) and '```' in turn['content'] 
        for turn in conversation
    )

def load_wildchat(max_records: int = config.WILDCHAT_MAX_RECORDS, use_local_shard: bool = True) -> pd.DataFrame:
    """Loads and filters the WildChat dataset for prompt quality training.

    Args:
        max_records: Maximum number of qualifying records to ingest.
        use_local_shard: If true, prioritizes high-speed local parity shards.

    Returns:
        pd.DataFrame: A filtered collection of developer chat interactions.
    """
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    parquet_path = os.path.join(data_dir, 'wildchat_shard.parquet')

    if use_local_shard and os.path.exists(parquet_path):
        logger.info(f"Loading actual WildChat data from local shard: {parquet_path}")
        try:
            # We only need the conversation column
            df = pd.read_parquet(parquet_path, columns=['conversation'])
            logger.info(f"Processing {len(df)} records for coding filters...")
            
            # Use faster filtering
            def filter_func(conv):
                if len(conv) < config.WILDCHAT_MIN_TURNS:
                    return False
                return any('```' in str(turn.get('content', '')) for turn in conv)

            # We'll do it in chunks or use a more explicit loop to show progress
            filtered_records = []
            count = 0
            for idx, conv in enumerate(df['conversation']):
                if filter_func(conv):
                    filtered_records.append({'conversation': conv})
                    if len(filtered_records) >= max_records:
                        break
                if idx % 5000 == 0 and idx > 0:
                    logger.info(f"Scanned {idx} records, found {len(filtered_records)} targets...")
            
            final_df = pd.DataFrame(filtered_records)
            logger.info(f"Filtered {len(final_df)} 'actual' records from shard.")
            return final_df
        except Exception as e:
            logger.error(f"Error reading WildChat parquet: {e}")
            # Fallback to streaming if parquet fails
    
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
