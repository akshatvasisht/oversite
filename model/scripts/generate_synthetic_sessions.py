import json
import os
import logging
import random
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_synthetic_sessions(output_dir: str = "data/synthetic") -> None:
    """
    Generates 20 mock End-to-End JSON session traces spanning the 3 profiles:
    - 5 Strategic
    - 5 Balanced
    - 10 Over-reliant (common baseline)
    
    Each session JSON mocks the 16-feature Component 1 vector, the Component 2 prompt
    strings, and the Component 3 chunk decisions.
    """
    os.makedirs(output_dir, exist_ok=True)
    profiles = ['strategic'] * 5 + ['balanced'] * 5 + ['over_reliant'] * 10
    
    # Shuffle for realism
    random.seed(config.RANDOM_SEED)
    random.shuffle(profiles)
    
    sessions = []
    
    for idx, profile in enumerate(profiles):
        session_id = f"mock-session-{profile}-{idx:02d}"
        
        # 1. Component 1 Mock Features
        if profile == 'strategic':
            behavioral_events = {
                'deliberation_time_avg': random.uniform(25.0, 60.0),
                'verification_frequency': random.randint(3, 8),
                'time_by_panel_editor_pct': random.uniform(0.60, 0.85),
                'acceptance_rate': random.uniform(0.3, 0.7)
            }
        elif profile == 'balanced':
            behavioral_events = {
                'deliberation_time_avg': random.uniform(10.0, 30.0),
                'verification_frequency': random.randint(1, 4),
                'time_by_panel_editor_pct': random.uniform(0.40, 0.60),
                'acceptance_rate': random.uniform(0.5, 0.9)
            }
        else: # Over-reliant
            behavioral_events = {
                'deliberation_time_avg': random.uniform(1.0, 10.0),
                'verification_frequency': random.randint(0, 1),
                'time_by_panel_editor_pct': random.uniform(0.10, 0.35),
                'acceptance_rate': random.uniform(0.85, 1.0)
            }
            
        # 2. Component 2 Mock Prompts
        if profile == 'strategic':
            prompts = [
                "The `BinaryTree` class lacks a balance check. Refactor it to enforce AVL balancing on insertion.",
                "Line 42 throws a KeyError. Must catch the exception and fallback to DefaultDict."
            ]
        elif profile == 'balanced':
            prompts = [
                "Add an insert method to the tree.",
                "How do I fix this error?"
            ]
        else: # Over-reliant
            prompts = [
                "write a tree",
                "it broke",
                "fix it",
                "try again"
            ]
            
        # 3. Component 3 Mock Chunk Decisions
        if profile == 'strategic':
            decisions = [
                {'decision': 'modified', 'proposed_code': 'def foo(): return 1', 'final_code': 'def foo(x=1): return x'},
                {'decision': 'modified', 'proposed_code': 'if x: pass', 'final_code': 'if x and y:\n    do_work()'}
            ]
        elif profile == 'balanced':
            decisions = [
                {'decision': 'accepted', 'proposed_code': 'def foo(): return 1', 'final_code': 'def foo(): return 1'},
                {'decision': 'modified', 'proposed_code': 'if x: pass', 'final_code': 'if x: do_work()'}
            ]
        else: # Over-reliant
            decisions = [
                {'decision': 'accepted', 'proposed_code': 'def foo(): return 1', 'final_code': 'def foo(): return 1'},
                {'decision': 'accepted', 'proposed_code': 'if x: pass', 'final_code': 'if x: pass'}
            ]
            
        session = {
            'session_id': session_id,
            'ground_truth_profile': profile,
            'behavioral_events': behavioral_events,
            'prompt_data': prompts,
            'review_decisions': decisions
        }
        
        sessions.append(session)
        
        # Write individual file
        file_path = os.path.join(output_dir, f"{session_id}.json")
        with open(file_path, 'w') as f:
            json.dump(session, f, indent=2)
            
    logger.info(f"Generated {len(sessions)} synthetic sessions targeting the 3 behavioral profiles in {output_dir}")

if __name__ == "__main__":
    generate_synthetic_sessions()
