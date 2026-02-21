import os
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelConfig:
    # Dataset Names
    CUPS_DATASET: str = "microsoft/coderec_programming_states"
    WILDCHAT_DATASET: str = "allenai/WildChat-1M"
    
    # Paths
    ARTIFACTS_DIR: str = "artifacts"
    EDA_DIR: str = os.path.join(ARTIFACTS_DIR, "eda")
    
    # Labeling Thresholds (Quantiles)
    LOW_THRESHOLD: float = 0.33
    HIGH_THRESHOLD: float = 0.66
    
    # ML Hyperparameters
    RANDOM_SEED: int = 42
    
    # Data Loading
    WILDCHAT_MAX_RECORDS: int = 500
    WILDCHAT_MIN_TURNS: int = 3

config = ModelConfig()

# Ensure directories exist
os.makedirs(config.EDA_DIR, exist_ok=True)
