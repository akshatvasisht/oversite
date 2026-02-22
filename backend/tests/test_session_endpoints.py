from helpers import start_session, make_session, get_events

# start_session is already imported from helpers, but we can override it if we want custom project_name etc.
# Actually, the test file's start_session was slightly more specific.
# In helpers.py, start_session exists.

def get_session_id(client):
    return make_session(client)

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
