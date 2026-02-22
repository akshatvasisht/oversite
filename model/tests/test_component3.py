import pytest
from component3 import component3_score

def test_zero_decisions_neutral_score():
    assert component3_score([]) == 3.0

def test_passive_acceptance_scores_low():
    # 0 edit distance
    decisions = [
        {
            'decision': 'accepted',
            'proposed_code': 'def foo():\n    return 42',
            'final_code': 'def foo():\n    return 42' # No change
        }
    ]
    assert component3_score(decisions) == 1.0

def test_slight_modification_scores_medium():
    # Minor edit: changed 42 to 43 (1 char diff on 25 char string) = 4% edit rate -> 1.0
    # Let's change 3 chars: "42" to "100" -> 3 char edit on 25 -> 12% edit rate -> 2.0
    decisions = [
        {
            'decision': 'modified',
            'proposed_code': 'def foo():\n    return 42',
            'final_code': 'def foo():\n    return 100'
        }
    ]
    assert component3_score(decisions) == 2.0
    
def test_balanced_tweaks_scores_3():
    # Proposed: "def foo():\n    return 42" (24 chars)
    # Modified: "def foo():\n    return val * 2" (29 chars)
    # "42" -> "val * 2" is an edit distance of 7 on a 24 char string -> 29% edit rate -> 3.0
    decisions = [
        {
            'decision': 'modified',
            'proposed_code': 'def foo():\n    return 42',
            'final_code': 'def foo():\n    return val * 2'
        }
    ]
    assert component3_score(decisions) == 3.0

def test_heavy_modification_scores_high():
    # Strategic rewriting. Total rewrite of body.
    # Proposed: 25 chars.
    decisions = [
        {
            'decision': 'modified',
            'proposed_code': 'def foo():\n    return 42',
            'final_code': 'def foo(x):\n    val = x * 2\n    return val'
        }
    ]
    # This distance is massive (> 60%), expect 5.0
    assert component3_score(decisions) == 5.0

def test_rejected_chunks_ignored():
    # Rejected code should not drag down the edit rate average
    decisions = [
        {
            'decision': 'rejected',
            'proposed_code': 'def bar(): pass',
            'final_code': 'def original(): pass' 
        },
        {
            'decision': 'accepted',
            'proposed_code': 'def foo():\n    return 42',
            'final_code': 'def foo():\n    return 42' # 0 distance -> 1.0
        }
    ]
    assert component3_score(decisions) == 1.0
