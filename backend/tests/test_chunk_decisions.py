import pytest
from unittest.mock import patch
from sqlalchemy.orm import sessionmaker

# Import fixtures from conftest (if any) or existing patterns.
# Since test_suggestions has fixtures, we will redefine them locally if needed or import them if possible.
# Actually, the fixtures `app`, `client`, `engine` are defined in test_suggestions, 
# so we might need to recreate them here or they are in conftest? Wait, they are inside test_suggestions.
# We will define our own fixtures following the same pattern.
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from base import Base
from routes.session import session_bp
from routes.files import files_bp
from routes.ai import ai_bp
from routes.suggestions import suggestions_bp
from routes.events import events_bp
from models import ChunkDecision, Event, AISuggestion

@pytest.fixture(autouse=True)
def _stub_gemini():
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    mock_client.assistant_call.return_value = "Here is a solution:\n```python\nreturn 42\n```"
    with patch("routes.ai.GeminiClient", return_value=mock_client):
        yield mock_client

@pytest.fixture
def engine():
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)

@pytest.fixture
def app(engine):
    TestSession = sessionmaker(bind=engine)

    def mock_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    flask_app = Flask(__name__)
    flask_app.register_blueprint(session_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(files_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(ai_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(suggestions_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(events_bp, url_prefix="/api/v1")
    flask_app.config["TESTING"] = True

    with patch("routes.session.get_db", mock_get_db):
        yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

# --- Helpers ---
def make_session(client):
    r = client.post("/api/v1/session/start", json={"username": "alice", "project_name": "test"})
    return r.get_json()["session_id"]

def make_file(client, sid):
    r = client.post(
        "/api/v1/files",
        json={"filename": "solution.py", "initial_content": "# start"},
        headers={"X-Session-ID": sid},
    )
    return r.get_json()["file_id"]

def make_interaction(client, sid):
    r = client.post(
        "/api/v1/ai/chat",
        json={"prompt": "write binary search"},
        headers={"X-Session-ID": sid},
    )
    return r.get_json()["interaction_id"]

def post_suggestion(client, sid, fid, interaction_id, original="def foo():\n    return 1\n", proposed="def foo():\n    return 2\n"):
    return client.post(
        "/api/v1/suggestions",
        json={
            "interaction_id": interaction_id,
            "file_id": fid,
            "original_content": original,
            "proposed_content": proposed,
        },
        headers={"X-Session-ID": sid},
    )

def setup_suggestion_with_hunks(client, engine, hunks_count=2):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]

    Session = sessionmaker(bind=engine)
    db = Session()
    s = db.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()
    s.hunks_count = hunks_count
    db.commit()
    db.close()

    return sid, suggestion_id

def decide_chunk(client, sid, suggestion_id, chunk_index, decision="accepted", time_ms=2000, final_code="code"):
    return client.post(
        f"/api/v1/suggestions/{suggestion_id}/chunks/{chunk_index}/decide",
        json={
            "decision": decision,
            "final_code": final_code,
            "time_on_chunk_ms": time_ms
        },
        headers={"X-Session-ID": sid}
    )

# --- Tests ---

def test_happy_path_chunk_decisions(client, engine):
    sid, suggestion_id = setup_suggestion_with_hunks(client, engine, 2)

    # Decide chunk 0 (Accepted)
    r1 = decide_chunk(client, sid, suggestion_id, 0, decision="accepted", time_ms=5000, final_code="pass")
    assert r1.status_code == 201
    assert "decision_id" in r1.get_json()

    # Verify DB state for chunk 0
    Session = sessionmaker(bind=engine)
    db = Session()
    cd1 = db.query(ChunkDecision).filter_by(suggestion_id=suggestion_id, chunk_index=0).first()
    assert cd1 is not None
    assert cd1.decision == "accepted"
    assert cd1.final_code == "pass"
    assert cd1.time_on_chunk_ms == 5000

    ev1 = db.query(Event).filter_by(session_id=sid, event_type="chunk_accepted").first()
    assert ev1 is not None

    s = db.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()
    assert s.resolved_at is None

    # Decide chunk 1 (Rejected)
    r2 = decide_chunk(client, sid, suggestion_id, 1, decision="rejected", time_ms=2000, final_code="fail")
    assert r2.status_code == 201

    db.expire_all()
    cd2 = db.query(ChunkDecision).filter_by(suggestion_id=suggestion_id, chunk_index=1).first()
    assert cd2 is not None
    assert cd2.decision == "rejected"

    ev2 = db.query(Event).filter_by(session_id=sid, event_type="chunk_rejected").first()
    assert ev2 is not None

    s2 = db.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()
    assert s2.resolved_at is not None
    assert s2.all_accepted is False
    assert s2.any_modified is False
    db.close()

def test_modified_decision(client, engine):
    sid, suggestion_id = setup_suggestion_with_hunks(client, engine, 1)

    r = decide_chunk(client, sid, suggestion_id, 0, decision="modified", time_ms=2000, final_code="mutated")
    assert r.status_code == 201

    Session = sessionmaker(bind=engine)
    db = Session()
    ev = db.query(Event).filter_by(session_id=sid, event_type="chunk_modified").first()
    assert ev is not None

    s = db.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()
    assert s.resolved_at is not None
    assert s.any_modified is True
    db.close()

def test_clamping(client, engine):
    sid, suggestion_id = setup_suggestion_with_hunks(client, engine, 3)

    r1 = decide_chunk(client, sid, suggestion_id, 0, time_ms=50)
    r2 = decide_chunk(client, sid, suggestion_id, 1, time_ms=999999)
    r3 = decide_chunk(client, sid, suggestion_id, 2, time_ms=5000)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r3.status_code == 201

    Session = sessionmaker(bind=engine)
    db = Session()
    cd1 = db.query(ChunkDecision).filter_by(chunk_index=0).first()
    cd2 = db.query(ChunkDecision).filter_by(chunk_index=1).first()
    cd3 = db.query(ChunkDecision).filter_by(chunk_index=2).first()
    
    assert cd1.time_on_chunk_ms == 100
    assert cd2.time_on_chunk_ms == 300000
    assert cd3.time_on_chunk_ms == 5000
    db.close()

def test_already_decided_409(client, engine):
    sid, suggestion_id = setup_suggestion_with_hunks(client, engine, 2)

    r1 = decide_chunk(client, sid, suggestion_id, 0)
    assert r1.status_code == 201

    r2 = decide_chunk(client, sid, suggestion_id, 0)
    assert r2.status_code == 409

    Session = sessionmaker(bind=engine)
    db = Session()
    assert db.query(ChunkDecision).filter_by(chunk_index=0).count() == 1
    assert db.query(Event).filter(Event.event_type.like("chunk_%")).count() == 1
    db.close()

def test_invalid_chunk_index_400(client, engine):
    sid, suggestion_id = setup_suggestion_with_hunks(client, engine, 2)

    r = decide_chunk(client, sid, suggestion_id, 99)
    assert r.status_code == 400

    Session = sessionmaker(bind=engine)
    db = Session()
    assert db.query(ChunkDecision).count() == 0
    db.close()

def test_transaction_rollback_on_error(client, engine):
    sid, suggestion_id = setup_suggestion_with_hunks(client, engine, 2)

    # Mock write_event to throw an exception
    with patch("routes.suggestions.write_event", side_effect=Exception("Simulated Database Error")):
        r = decide_chunk(client, sid, suggestion_id, 0)
        assert r.status_code == 500

    Session = sessionmaker(bind=engine)
    db = Session()
    assert db.query(ChunkDecision).count() == 0
    assert db.query(Event).filter(Event.event_type.like("chunk_%")).count() == 0
    db.close()

def test_missing_session_header_401(client, engine):
    sid, suggestion_id = setup_suggestion_with_hunks(client, engine, 2)
    
    r = client.post(
        f"/api/v1/suggestions/{suggestion_id}/chunks/0/decide",
        json={"decision": "accepted", "final_code": "code", "time_on_chunk_ms": 2000}
    )
    assert r.status_code == 401
