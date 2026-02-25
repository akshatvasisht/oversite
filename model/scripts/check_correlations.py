import os
import sys
import pandas as pd
import numpy as np
import logging

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loader import load_cups
from labels import apply_proxy_labels
from features import extract_behavioral_features, FEATURE_NAMES, SessionTelemetry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_correlations():
    df_raw = load_cups()
    df = apply_proxy_labels(df_raw)
    
    LABEL_MAP = {'over_reliant': 0, 'balanced': 1, 'strategic': 2}
    df['target'] = df['proxy_label'].map(LABEL_MAP)
    
    feats_list = []
    for _, row in df.iterrows():
        telemetry: SessionTelemetry = {
            'decisions': [],
            'events': [],
            'interactions': [],
            'session_start': None,
            'precomputed': row.to_dict()
        }
        feats = extract_behavioral_features(telemetry)
        feats_list.append(feats)
        
    X = np.array(feats_list)
    y = df['target'].values
    
    correlations = {}
    for i, name in enumerate(FEATURE_NAMES):
        cor = np.corrcoef(X[:, i], y)[0, 1]
        correlations[name] = cor
        
    print("\nFeature-Target Correlations (Sorted):")
    print("-" * 40)
    sorted_cors = sorted(correlations.items(), key=lambda x: abs(x[1]) if not np.isnan(x[1]) else 0, reverse=True)
    for name, cor in sorted_cors:
        print(f"{name:30} | {cor:+.4f}")

if __name__ == "__main__":
    check_correlations()
