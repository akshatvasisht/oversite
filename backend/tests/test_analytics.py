import pytest
import uuid
from datetime import datetime, timezone
from app import app
from db import get_db, init_db
from schema import Session, SessionScore

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_overview_filters_correctly(client):
    db = next(get_db())
    # Seed data
    s1_id = uuid.uuid4().hex
    s2_id = uuid.uuid4().hex
    s1 = Session(session_id=s1_id, username="test1", started_at=datetime.now(timezone.utc), ended_at=datetime.now(timezone.utc))
    s2 = Session(session_id=s2_id, username="test2", started_at=datetime.now(timezone.utc), ended_at=None)
    db.add(s1)
    db.add(s2)
    db.commit()

    resp = client.get('/api/v1/analytics/overview?completed_only=true', headers={'Authorization': 'Bearer mock-jwt-admin-admin1'})
    data = resp.get_json()
    assert len(data['sessions']) >= 1
    session_ids = [s['session_id'] for s in data['sessions']]
    assert s1_id in session_ids
    assert s2_id not in session_ids
    
def test_session_analytics_returns_expected_keys(client):
    db = next(get_db())
    s3_id = uuid.uuid4().hex
    s3 = Session(session_id=s3_id, username="test3", started_at=datetime.now(timezone.utc), ended_at=datetime.now(timezone.utc))
    db.add(s3)
    db.commit()
    
    resp = client.get(f'/api/v1/analytics/session/{s3_id}', headers={'Authorization': 'Bearer mock-jwt-admin-admin1'})
    assert resp.status_code == 200
    data = resp.get_json()
    
    expected_keys = [
        "overall_label", "weighted_score", "structural_scores",
        "prompt_quality_scores", "review_scores", "rate_acceptance",
        "duration_deliberation_avg", "session_id", "status"
    ]
    for key in expected_keys:
        assert key in data
