import pytest
import sys
from unittest.mock import patch, MagicMock
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from base import Base
from helpers import make_session, make_file, post_file, get_events

@pytest.fixture(autouse=True)
def _stub_diff():
    """Install a diff stub per-test."""
    mock_diff = MagicMock()
    mock_diff.compute_edit_delta.return_value = "--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new"
    with patch("routes.files.compute_edit_delta", mock_diff.compute_edit_delta):
        yield mock_diff

# --- POST /files ---

def test_create_file_returns_file_id(client):
    sid = make_session(client)
    r = post_file(client, sid)
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
    post_file(client, sid, filename="solution.py")
    events = get_events(client, sid)
    assert any(e["event_type"] == "file_open" and e["content"] == "solution.py" for e in events)


def test_create_file_with_empty_initial_content(client):
    sid = make_session(client)
    r = post_file(client, sid, content="")
    assert r.status_code == 201


# --- POST /files/<file_id>/save ---

def test_save_file_success(client):
    sid = make_session(client)
    file_id = make_file(client, sid)
    r = client.post(
        f"/api/v1/files/{file_id}/save",
        json={"content": "def solution():\n    return 42"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 200
    assert "event_id" in r.get_json()
    assert "saved_at" in r.get_json()


def test_save_file_writes_edit_event(client):
    sid = make_session(client)
    file_id = make_file(client, sid)
    client.post(
        f"/api/v1/files/{file_id}/save",
        json={"content": "new content"},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    assert any(e["event_type"] == "edit" for e in events)


def test_save_file_missing_content(client):
    sid = make_session(client)
    file_id = make_file(client, sid)
    r = client.post(
        f"/api/v1/files/{file_id}/save",
        json={},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_save_file_wrong_session(client):
    sid1 = make_session(client, username="alice")
    sid2 = make_session(client, username="bob")
    file_id = make_file(client, sid1)
    r = client.post(
        f"/api/v1/files/{file_id}/save",
        json={"content": "new content"},
        headers={"X-Session-ID": sid2},
    )
    assert r.status_code == 404


# --- POST /events/file ---

def test_file_close_event(client):
    sid = make_session(client)
    file_id = make_file(client, sid)
    r = client.post(
        "/api/v1/events/file",
        json={"file_id": file_id, "event_type": "file_close"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 200
    assert "event_id" in r.get_json()


def test_file_reopen_writes_second_open_event(client):
    sid = make_session(client)
    file_id = make_file(client, sid)
    client.post("/api/v1/events/file", json={"file_id": file_id, "event_type": "file_close"}, headers={"X-Session-ID": sid})
    client.post("/api/v1/events/file", json={"file_id": file_id, "event_type": "file_open"}, headers={"X-Session-ID": sid})
    events = get_events(client, sid)
    file_opens = [e for e in events if e["event_type"] == "file_open"]
    assert len(file_opens) == 2  # initial create + reopen


def test_file_event_invalid_type(client):
    sid = make_session(client)
    file_id = make_file(client, sid)
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
