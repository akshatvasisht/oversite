import schema
import time
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import sessionmaker
from helpers import start_session, seed_complete_session

@patch("services.scoring.GeminiClient")
def test_full_pipeline_on_end_session(mock_gemini_class, client, engine):
    # Setup mock
    mock_client = MagicMock()
    mock_client.judge_call.return_value = "This is a great candidate narrative."
    mock_gemini_class.return_value = mock_client
    
    sid = "full-test-sid"
    TestSession = sessionmaker(bind=engine)
    db = TestSession()
    seed_complete_session(db, sid)
    db.close()
    
    # End session via API
    r = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r.status_code == 200
    
    # Verify SessionScore created
    db = TestSession()
    score = db.query(schema.SessionScore).filter_by(session_id=sid).first()
    assert score is not None
    assert score.overall_label in ["strategic", "balanced", "over_reliant"]
    assert score.weighted_score > 0
    
    # Wait for async thread (up to 2 seconds)
    for _ in range(20):
        db.refresh(score)
        if score.llm_narrative:
            break
        time.sleep(0.1)
    
    assert score.llm_narrative == "This is a great candidate narrative."
    db.close()
