import logging
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def _levenshtein_distance(s1: str, s2: str) -> int:
    """Computes the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def component3_score(decisions: List[Dict[str, Any]]) -> float:
    """
    Computes the Component 3 (Critical Review) score based on post-acceptance edit rate.
    
    The input list should contain dictionaries mapping to the `chunk_decisions` table:
    {
        'decision_id': ...,
        'original_code': str,
        'proposed_code': str,
        'final_code': str,
        'decision': 'accepted' | 'rejected' | 'modified'
    }
    
    We focus on 'accepted' and 'modified' chunks.
    The heuristic threshold percentiles (based on CUPS user study distribution):
      > 60% modified = 5.0 (Strategic rewriting/Heavy customization)
      > 35% modified = 4.0 (Active iteration)
      > 15% modified = 3.0 (Balanced tweaks)
      > 5%  modified = 2.0 (Minor fixes)
      <= 5% modified = 1.0 (Passive acceptance / Over-reliant)
      
    Returns:
        float: A score between 1.0 and 5.0
    """
    if not decisions:
        logger.warning("No chunk decisions provided. Defaulting to Neutral score (3.0)")
        return 3.0
        
    total_proposed_len = 0
    total_edit_distance = 0
    
    for chunk in decisions:
        # We only care about chunks where the AI's code was brought into the file.
        # If it was rejected outright, there's no "post-acceptance edit" to measure.
        if chunk.get('decision') in ['accepted', 'modified']:
            proposed = chunk.get('proposed_code', '')
            final = chunk.get('final_code', '')
            
            # Distance from what the AI proposed to what the user ultimately left in the file
            dist = _levenshtein_distance(proposed, final)
            
            total_proposed_len += len(proposed)
            total_edit_distance += dist

    # If they never accepted anything, we can't measure post-acceptance edit rate.
    if total_proposed_len == 0:
        return 3.0
        
    edit_rate = total_edit_distance / total_proposed_len
    
    # Map edit_rate to human-centric label score based on agreed percentiles
    if edit_rate > 0.60:
        return 5.0
    elif edit_rate > 0.35:
        return 4.0
    elif edit_rate > 0.15:
        return 3.0
    elif edit_rate > 0.05:
        return 2.0
    else:
        return 1.0
