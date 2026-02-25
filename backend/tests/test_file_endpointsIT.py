from helpers import make_session, make_file, post_file, get_events

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


# --- POST /files/<file_id>/save (uses real diff) ---

def test_save_file_success(client):
    sid = make_session(client)
    file_id = make_file(client, sid)
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
    file_id = make_file(client, sid, content="# start\n")
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


def test_save_file_identical_content_produces_empty_delta(client):
    content = "def foo():\n    return 1\n"
    sid = make_session(client)
    file_id = make_file(client, sid, content=content)
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
