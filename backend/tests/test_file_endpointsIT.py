"""
Integration tests for file endpoints — uses the real diff.py (no mock).
Run after diff.py is implemented.
"""
import pytest
from unittest.mock import patch
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from base import Base
from routes.session import session_bp
from routes.files import files_bp
import models


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
    flask_app.config["TESTING"] = True

    with patch("routes.session.get_db", mock_get_db):
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# --- helpers ---

def make_session(client):
    r = client.post("/api/v1/session/start", json={"username": "alice", "project_name": "test"})
    return r.get_json()["session_id"]


def make_file(client, sid, filename="solution.py", initial_content="# start"):
    return client.post(
        "/api/v1/files",
        json={"filename": filename, "initial_content": initial_content},
        headers={"X-Session-ID": sid},
    )


def get_events(client, sid):
    return client.get(f"/api/v1/session/{sid}/trace").get_json()["events"]


# --- POST /files ---

def test_create_file_returns_file_id(client):
    sid = make_session(client)
    r = make_file(client, sid)
    assert r.status_code == 201
    assert "file_id" in r.get_json()
    assert "created_at" in r.get_json()


def test_create_file_missing_filename(client):
    sid = make_session(client)
    r = client.post("/api/v1/files", json={}, headers={"X-Session-ID": sid})
    assert r.status_code == 400


def test_create_file_missing_session_header(client):
    r = client.post("/api/v1/files", json={"filename": "solution.py"})
    assert r.status_code == 401


def test_create_file_writes_file_open_event(client):
    sid = make_session(client)
    make_file(client, sid, filename="solution.py")
    events = get_events(client, sid)
    assert any(e["event_type"] == "file_open" and e["content"] == "solution.py" for e in events)


def test_create_file_with_empty_initial_content(client):
    sid = make_session(client)
    r = make_file(client, sid, initial_content="")
    assert r.status_code == 201


# --- POST /files/<file_id>/save (uses real diff) ---

def test_save_file_success(client):
    sid = make_session(client)
    file_id = make_file(client, sid).get_json()["file_id"]
    r = client.post(
        f"/api/v1/files/{file_id}/save",
        json={"content": "def solution():\n    return 42\n"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 200
    assert "event_id" in r.get_json()
    assert "saved_at" in r.get_json()


def test_save_file_writes_edit_event_with_real_diff(client):
    sid = make_session(client)
    file_id = make_file(client, sid, initial_content="# start\n").get_json()["file_id"]
    client.post(
        f"/api/v1/files/{file_id}/save",
        json={"content": "def solution():\n    return 42\n"},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    edit_events = [e for e in events if e["event_type"] == "edit"]
    assert len(edit_events) == 1
    # content field on the edit event is the unified diff string
    delta = edit_events[0]["content"]
    assert "@@" in delta
    assert "-# start" in delta
    assert "+def solution" in delta


def test_save_file_missing_content(client):
    sid = make_session(client)
    file_id = make_file(client, sid).get_json()["file_id"]
    r = client.post(
        f"/api/v1/files/{file_id}/save",
        json={},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_save_file_wrong_session(client):
    sid1 = make_session(client)
    sid2 = make_session(client)
    file_id = make_file(client, sid1).get_json()["file_id"]
    r = client.post(
        f"/api/v1/files/{file_id}/save",
        json={"content": "new content"},
        headers={"X-Session-ID": sid2},
    )
    assert r.status_code == 404


def test_save_file_identical_content_produces_empty_delta(client):
    content = "def foo():\n    return 1\n"
    sid = make_session(client)
    file_id = make_file(client, sid, initial_content=content).get_json()["file_id"]
    client.post(
        f"/api/v1/files/{file_id}/save",
        json={"content": content},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    edit_events = [e for e in events if e["event_type"] == "edit"]
    assert edit_events[0]["content"] == ""


# --- POST /events/file ---

def test_file_close_event(client):
    sid = make_session(client)
    file_id = make_file(client, sid).get_json()["file_id"]
    r = client.post(
        "/api/v1/events/file",
        json={"file_id": file_id, "event_type": "file_close"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 200
    assert "event_id" in r.get_json()


def test_file_reopen_writes_second_open_event(client):
    sid = make_session(client)
    file_id = make_file(client, sid).get_json()["file_id"]
    client.post("/api/v1/events/file", json={"file_id": file_id, "event_type": "file_close"}, headers={"X-Session-ID": sid})
    client.post("/api/v1/events/file", json={"file_id": file_id, "event_type": "file_open"}, headers={"X-Session-ID": sid})
    events = get_events(client, sid)
    file_opens = [e for e in events if e["event_type"] == "file_open"]
    assert len(file_opens) == 2  # initial create + reopen


def test_file_event_invalid_type(client):
    sid = make_session(client)
    file_id = make_file(client, sid).get_json()["file_id"]
    r = client.post(
        "/api/v1/events/file",
        json={"file_id": file_id, "event_type": "file_delete"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_file_event_invalid_file_id(client):
    sid = make_session(client)
    r = client.post(
        "/api/v1/events/file",
        json={"file_id": "does-not-exist", "event_type": "file_close"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 404
