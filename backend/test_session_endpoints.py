import pytest
from unittest.mock import patch
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from base import Base
from routes.session import session_bp
import models  # ensure all tables are registered on Base


@pytest.fixture
def engine():
    """Fresh in-memory SQLite DB per test."""
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
    flask_app.config["TESTING"] = True

    with patch("routes.session.get_db", mock_get_db):
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# --- helpers ---

def start_session(client, username="alice", project_name="test"):
    r = client.post("/api/v1/session/start", json={"username": username, "project_name": project_name})
    return r


def get_session_id(client):
    return start_session(client).get_json()["session_id"]


# --- tests ---

def test_start_session_returns_session_id(client):
    r = start_session(client)
    assert r.status_code == 201
    data = r.get_json()
    assert "session_id" in data
    assert "started_at" in data


def test_start_session_missing_username(client):
    r = client.post("/api/v1/session/start", json={"project_name": "test"})
    assert r.status_code == 400


def test_start_session_writes_orientation_event(client):
    sid = get_session_id(client)
    r = client.get(f"/api/v1/session/{sid}/trace")
    events = r.get_json()["events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "panel_focus"
    assert events[0]["content"] == "orientation"


def test_end_session_success(client):
    sid = get_session_id(client)
    r = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r.status_code == 200
    data = r.get_json()
    assert "duration_seconds" in data
    assert "ended_at" in data
    assert data["session_id"] == sid


def test_end_session_already_ended(client):
    sid = get_session_id(client)
    client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    r = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Session already ended"


def test_end_session_missing_header(client):
    r = client.post("/api/v1/session/end")
    assert r.status_code == 401


def test_end_session_invalid_session_id(client):
    r = client.post("/api/v1/session/end", headers={"X-Session-ID": "does-not-exist"})
    assert r.status_code == 404


def test_trace_returns_events(client):
    sid = get_session_id(client)
    r = client.get(f"/api/v1/session/{sid}/trace")
    assert r.status_code == 200
    data = r.get_json()
    assert data["session_id"] == sid
    assert isinstance(data["events"], list)


def test_trace_invalid_session(client):
    r = client.get("/api/v1/session/does-not-exist/trace")
    assert r.status_code == 404


def test_full_session_lifecycle(client):
    # start
    r = start_session(client, username="bob", project_name="two-sum")
    assert r.status_code == 201
    sid = r.get_json()["session_id"]

    # trace has orientation event
    events = client.get(f"/api/v1/session/{sid}/trace").get_json()["events"]
    assert any(e["event_type"] == "panel_focus" and e["content"] == "orientation" for e in events)

    # end
    r = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r.status_code == 200
    assert r.get_json()["duration_seconds"] >= 0

    # double end rejected
    r = client.post("/api/v1/session/end", headers={"X-Session-ID": sid})
    assert r.status_code == 400
