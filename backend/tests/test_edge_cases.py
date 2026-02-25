import pytest
import uuid
from datetime import datetime, timezone
from app import app
from db import get_db
from schema import Session, SessionScore, Event, AISuggestion, EditorEvent

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_empty_session_scores_without_crash(client):
    db = next(get_db())
    sid = str(uuid.uuid4())
    s = Session(session_id=sid, username="empty_user", started_at=datetime.now(timezone.utc))
    db.add(s)
    db.commit()

    # End the session without any events or prompts
    r = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r.status_code == 200

    # Ensure SessionScore created synchronously without crash
    score = db.query(SessionScore).filter_by(session_id=sid).first()
    assert score is not None
    assert score.overall_label == "Not Enough Data"
    assert score.weighted_score == 3.0

def test_double_session_end_returns_400(client):
    db = next(get_db())
    sid = str(uuid.uuid4())
    s = Session(session_id=sid, username="double_user", started_at=datetime.now(timezone.utc))
    db.add(s)
    db.commit()

    r1 = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r1.status_code == 200

    r2 = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r2.status_code == 400
    assert "already ended" in r2.get_json()["error"].lower()

def test_auth_login_success(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["role"] == "admin"
    assert data["token"] == "mock-jwt-admin-admin"

def test_auth_login_failure(client):
    r = client.post("/api/v1/auth/login", json={"username": "nonexistent"})
    assert r.status_code == 401

def test_analytics_requires_admin_role(client):
    r = client.get("/api/v1/analytics/overview")
    assert r.status_code == 401 # Missing token
    
    r = client.get("/api/v1/analytics/overview", headers={"Authorization": "Bearer mock-jwt-candidate-candidate"})
    assert r.status_code == 403 # Insufficient permissions

    r = client.get("/api/v1/analytics/overview", headers={"Authorization": "Bearer mock-jwt-admin-admin"})
    assert r.status_code == 200 # Success

def test_dual_write_rolls_back_on_db_error(client, monkeypatch):
    db = next(get_db())
    sid = str(uuid.uuid4())
    fid = str(uuid.uuid4())
    s = Session(session_id=sid, username="rollback_user", started_at=datetime.now(timezone.utc))
    db.add(s)
    db.commit()
    
    # We will simulate a crash during db.commit in the suggestion endpoint
    def mock_commit(*args, **kwargs):
        raise Exception("Simulated DB Error")
        
    import sqlalchemy.orm.session
    monkeypatch.setattr(sqlalchemy.orm.session.Session, "commit", mock_commit)

    with pytest.raises(Exception, match="Simulated DB Error"):
        r = client.post(
            "/api/v1/suggestions", 
            json={
                "interaction_id": "i1", 
                "file_id": fid, 
                "original_content": "a", 
                "proposed_content": "b"
            },
            headers={"X-Session-ID": sid}
        )
    
    # After the failed request, verify rows were rolled back
    result = db.query(AISuggestion).filter_by(session_id=sid).first()
    assert result is None
    result_event = db.query(EditorEvent).filter_by(session_id=sid).first()
    assert result_event is None
