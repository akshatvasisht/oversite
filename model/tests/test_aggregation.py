import pytest
from aggregation import aggregate_scores

def score_session(profile: str) -> tuple[float, float, float]:
    """
    Simulates the pipeline outputs for specific profiles.
    Returns (c1_score, c2_score, c3_score)
    """
    if profile == 'strategic':
        # High structural interaction, strong specific prompts, high edit rate
        return (4.5, 4.0, 4.8)
    elif profile == 'balanced':
        # Moderate across the board
        return (3.2, 3.5, 3.0)
    elif profile == 'over_reliant':
        # Low structural score (passive), vague prompts, zero edits
        return (1.5, 2.0, 1.0)
    else:
        return (3.0, 3.0, 3.0)

# Generate 10 mock sessions comparing a strategic user to an over_reliant user
test_pairs = [
    ('strategic', 'over_reliant'),
    ('strategic', 'over_reliant'),
    ('strategic', 'over_reliant'),
    ('strategic', 'over_reliant'),
    ('strategic', 'over_reliant'),
    # Add some noise/variance to the scores for realism
    ('strategic_variant1', 'over_reliant_variant1'),
    ('strategic', 'balanced'), # Strategic should also beat balanced
    ('strategic_variant2', 'over_reliant_variant2'),
    ('strategic', 'over_reliant'),
    ('strategic', 'over_reliant'),
]

def noisy_score_session(profile: str):
    if profile == 'strategic_variant1': return (3.8, 3.9, 4.0)
    if profile == 'strategic_variant2': return (4.0, 4.5, 3.5)
    if profile == 'over_reliant_variant1': return (2.5, 2.0, 1.5)
    if profile == 'over_reliant_variant2': return (1.8, 2.8, 1.2)
    return score_session(profile)

def test_contrastive_discrimination():
    """
    Validates that a strategic profile scores higher than an over_reliant
    profile in at least 8 out of 10 paired tasks.
    """
    results = []
    for strategic, overreliant in test_pairs:
        s_score, s_label = aggregate_scores(*noisy_score_session(strategic))
        o_score, o_label = aggregate_scores(*noisy_score_session(overreliant))
        
        # We expect the overall weighted score to be strictly greater
        # and the string labels to reflect the dominance
        if s_score > o_score:
            results.append(True)
        else:
            results.append(False)
            
    assert sum(results) >= 8  # 8 of 10 must pass

def test_label_thresholds():
    """Validates the discrete mapping of 1-5 float to the String labels."""
    # A score array of [2.0, 2.0, 2.0] averages to 2.0 -> "over_reliant"
    assert aggregate_scores(2.0, 2.0, 2.0)[1] == 'over_reliant'
    
    # A score array of [3.0, 3.0, 3.0] averages to 3.0 -> "balanced"
    assert aggregate_scores(3.0, 3.0, 3.0)[1] == 'balanced'
    
    # A score array of [4.0, 4.0, 4.0] averages to 4.0 -> "strategic"
    assert aggregate_scores(4.0, 4.0, 4.0)[1] == 'strategic'
    
def test_importance_weighting():
    """Verifies that giving skewed importances shifts the final score toward the dominant feature."""
    importances = {
        'deliberation_time_avg': 0.6,
        'verification_frequency': 0.2
    } # High C1 weight (sum = 0.8)
    
    # C1 is perfect (5.0), the rest are terrible (1.0)
    biased_score, biased_label = aggregate_scores(5.0, 1.0, 1.0, importances)
    
    # Flat average would be (5+1+1)/3 = 2.33
    # Weighted average should favor the 5.0 (C1 gets 50% weight -> 5*0.5 + 1*0.25 + 1*0.25 = 2.5 + 0.25 + 0.25 = 3.0)
    assert biased_score >= 3.0
    
    flat_score, flat_label = aggregate_scores(5.0, 1.0, 1.0)
    assert flat_score < biased_score
    
