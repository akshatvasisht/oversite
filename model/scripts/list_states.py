import os
import sys
import pandas as pd
import numpy as np

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def list_states():
    pkl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'data_labeled_study.pkl')
    user_dfs = pd.read_pickle(pkl_path)
    
    all_labeled_states = []
    all_state_names = []
    
    for df in user_dfs:
        if 'LabeledState' in df.columns:
            all_labeled_states.extend(df['LabeledState'].unique().tolist())
        if 'StateName' in df.columns:
            all_state_names.extend(df['StateName'].unique().tolist())
            
    print("Unique LabeledState values:")
    print(set(all_labeled_states))
    print("\nUnique StateName values:")
    print(set(all_state_names))

if __name__ == "__main__":
    list_states()
