import pytest
from unittest.mock import patch, MagicMock
from helpers import make_session, make_file, get_events

def start_session(client, username="alice", project_name="test"):
    return client.post("/api/v1/session/start", json={"username": username, "project_name": project_name})

def get_session_id(client):
    return make_session(client)

@pytest.fixture(autouse=True)
def _stub_diff():
    """Install a diff stub per-test."""
    mock_diff = MagicMock()
    mock_diff.compute_edit_delta.return_value = "--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new"
    with patch("routes.events.compute_edit_delta", mock_diff.compute_edit_delta):
        yield mock_diff

# --- POST /events/editor ---

def test_editor_event_returns_201_and_event_id(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    r = client.post(
        "/api/v1/events/editor",
        json={"file_id": fid, "content": "def foo():\n    return 1\n"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 201
    data = r.get_json()
    assert "event_id" in data
    assert "recorded_at" in data


def test_editor_event_dual_writes_edit_event(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    client.post(
        "/api/v1/events/editor",
        json={"file_id": fid, "content": "new content"},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    event_types = [e["event_type"] for e in events]
    assert "edit" in event_types


def test_editor_event_edit_metadata_has_trigger_editor(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    client.post(
        "/api/v1/events/editor",
        json={"file_id": fid, "content": "new content"},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    edit_event = next(e for e in events if e["event_type"] == "edit")
    assert edit_event["metadata"]["trigger"] == "editor"


def test_editor_event_missing_file_id_returns_400(client):
    sid = make_session(client)
    r = client.post(
        "/api/v1/events/editor",
        json={"content": "hello"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_editor_event_missing_content_returns_400(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    r = client.post(
        "/api/v1/events/editor",
        json={"file_id": fid},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_editor_event_wrong_session_returns_404(client):
    sid1 = make_session(client, username="user1")
    sid2 = make_session(client, username="user2")
    fid = make_file(client, sid1)
    r = client.post(
        "/api/v1/events/editor",
        json={"file_id": fid, "content": "hello"},
        headers={"X-Session-ID": sid2},
    )
    assert r.status_code == 404


def test_editor_event_missing_session_header_returns_401(client):
    r = client.post("/api/v1/events/editor", json={"file_id": "x", "content": "y"})
    assert r.status_code == 401


def test_editor_event_calls_compute_edit_delta(_stub_diff, client):
    sid = make_session(client)
    fid = make_file(client, sid)
    client.post(
        "/api/v1/events/editor",
        json={"file_id": fid, "content": "new"},
        headers={"X-Session-ID": sid},
    )
    assert _stub_diff.compute_edit_delta.called


# --- POST /events/execute ---

def test_execute_event_returns_201_and_event_id(client):
    sid = make_session(client)
    r = client.post(
        "/api/v1/events/execute",
        json={"entrypoint": "test.py", "files": [{"filename": "test.py", "content": "print(1)"}]},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 200
    assert "event_id" in r.get_json()
    assert r.get_json()["exit_code"] == 0

def test_execute_event_dual_writes_execute_event(client):
    sid = make_session(client)
    client.post(
        "/api/v1/events/execute",
        json={"entrypoint": "test.py", "files": [{"filename": "test.py", "content": "print('hello')"}]},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    event_types = [e["event_type"] for e in events]
    assert "execute" in event_types

def test_execute_event_metadata_has_entrypoint(client):
    sid = make_session(client)
    client.post(
        "/api/v1/events/execute",
        json={"entrypoint": "main.py", "files": [{"filename": "main.py", "content": ""}]},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    exec_event = next(e for e in events if e["event_type"] == "execute")
    assert exec_event["metadata"]["entrypoint"] == "main.py"

def test_execute_event_missing_entrypoint_returns_400(client):
    sid = make_session(client)
    r = client.post(
        "/api/v1/events/execute",
        json={"files": []},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400

def test_execute_event_missing_session_header_returns_401(client):
    r = client.post("/api/v1/events/execute", json={"entrypoint": "test.py", "files": []})
    assert r.status_code == 401

# --- POST /events/panel ---

def test_panel_event_returns_201_and_event_id(client):
    sid = make_session(client)
    r = client.post(
        "/api/v1/events/panel",
        json={"panel": "editor"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 201
    assert "event_id" in r.get_json()


def test_panel_event_dual_writes_panel_focus_event(client):
    sid = make_session(client)
    client.post(
        "/api/v1/events/panel",
        json={"panel": "chat"},
        headers={"X-Session-ID": sid},
    )
    events = get_events(client, sid)
    panel_events = [e for e in events if e["event_type"] == "panel_focus"]
    contents = [e["content"] for e in panel_events]
    assert "chat" in contents


def test_panel_event_invalid_panel_returns_400(client):
    sid = make_session(client)
    r = client.post(
        "/api/v1/events/panel",
        json={"panel": "unknown_panel"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_panel_event_missing_panel_returns_400(client):
    sid = make_session(client)
    r = client.post(
        "/api/v1/events/panel",
        json={},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_panel_event_phase_values_are_valid(client):
    sid = make_session(client)
    for phase in ["orientation", "implementation", "verification"]:
        r = client.post(
            "/api/v1/events/panel",
            json={"panel": phase},
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 201


def test_panel_event_missing_session_header_returns_401(client):
    r = client.post("/api/v1/events/panel", json={"panel": "editor"})
    assert r.status_code == 401
