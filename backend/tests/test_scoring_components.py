from helpers import seed_rich_session
from services.scoring import extract_behavioral_features, run_behavioral_evaluation, run_prompt_evaluation, run_critical_review_evaluation, aggregate_scores

def test_extract_behavioral_features(db_session):
    sid = "test-session"
    seed_rich_session(db_session, sid)
    
    features = extract_behavioral_features(sid, db_session)
    assert len(features) == 16
    
    # FEATURE_NAMES order:
    # 0: acceptance_rate
    # 1: deliberation_time_avg
    # 5: chunk_acceptance_rate
    # 7: time_on_chunk_avg_ms
    
    assert features[0] == 0.0  # modified is not accepted verbatim
    assert features[1] == 5000.0 
    assert features[5] == 1.0  # modified counts towards chunk_acceptance_rate
    assert features[7] == 5000.0
    
    # orientation_duration_s (started_at to first edit/prompt)
    # started_at: now - 10m
    # e2 (edit): now - 8m
    # diff: 2m = 120s
    assert features[10] == 120.0 # FEATURE_NAMES[10] is orientation_duration_s
    
    # iteration_depth (edit -> execute cycles)
    # e2 (edit) -> e3 (execute) = 1 cycle
    assert features[11] == 1.0 # FEATURE_NAMES[11] is iteration_depth

def test_run_behavioral_evaluation(db_session):
    sid = "test-session"
    seed_rich_session(db_session, sid)
    res = run_behavioral_evaluation(sid, db_session)
    assert res['label'] == 'balanced'
    assert len(res['explanations']) > 0

def test_run_prompt_quality(db_session):
    sid = "test-session"
    seed_rich_session(db_session, sid)
    res = run_prompt_evaluation(sid, db_session)
    
    # prompt: "Refactor the logic to implement two sum? `int[] result`"
    # length 51 (>20: +1, >50: +0.5), has ` (+1), has "Refactor" (+0.5)
    # base 1.0 + 1.0 + 0.5 + 1.0 + 0.5 = 4.0
    assert res['score'] == 4.0
    assert len(res['per_prompt']) == 1

def test_run_critical_review(db_session):
    sid = "test-session"
    seed_rich_session(db_session, sid)
    res = run_critical_review_evaluation(sid, db_session)
    assert res['score'] == 4.5 # modified = 4.5

def test_aggregation():
    c1 = {"score": 4.5} # strategic
    c2 = {"score": 4.5}
    c3 = {"score": 4.5}
    score, label = aggregate_scores(c1, c2, c3)
    assert label == "strategic"
    assert round(score, 2) == 4.5

def test_run_component1_fallback(db_session):
    sid = "test-session"
    seed_rich_session(db_session, sid)
    from unittest.mock import patch
    with patch("services.scoring.load_models", return_value={}):
        res = run_behavioral_evaluation(sid, db_session)
        assert res['fallback'] == True
        assert res['label'] == "balanced"
        assert res['score'] == 3.0
