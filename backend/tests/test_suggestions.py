from helpers import (
    make_session, make_file, make_interaction, 
    post_suggestion, resolve_suggestion, get_events
)

# Rename resolve_suggestion locally if needed or just use it
resolve = resolve_suggestion

# --- POST /suggestions ---

def test_post_suggestion_returns_201_and_fields(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    assert r.status_code == 201
    data = r.get_json()
    assert "suggestion_id" in data
    assert "shown_at" in data
    assert data["original_content"] == "def foo():\n    return 1\n"
    assert data["proposed_content"] == "def foo():\n    return 2\n"


def test_identical_content_returns_400(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid, original="same", proposed="same")
    assert r.status_code == 400


def test_missing_interaction_id_returns_400(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    r = client.post(
        "/api/v1/suggestions",
        json={"file_id": fid, "original_content": "a", "proposed_content": "b"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_missing_file_id_returns_400(client):
    sid = make_session(client)
    iid = make_interaction(client, sid)
    r = client.post(
        "/api/v1/suggestions",
        json={"interaction_id": iid, "original_content": "a", "proposed_content": "b"},
        headers={"X-Session-ID": sid},
    )
    assert r.status_code == 400


def test_missing_session_header_returns_401(client):
    r = client.post(
        "/api/v1/suggestions",
        json={"interaction_id": "x", "file_id": "y", "original_content": "a", "proposed_content": "b"},
    )
    assert r.status_code == 401


def test_suggestion_dual_writes_suggestion_shown_event(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    post_suggestion(client, sid, fid, iid)
    events = get_events(client, sid)
    event_types = [e["event_type"] for e in events]
    assert "suggestion_shown" in event_types


def test_suggestion_shown_event_metadata_has_suggestion_id(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]
    events = get_events(client, sid)
    shown_event = next(e for e in events if e["event_type"] == "suggestion_shown")
    assert shown_event["metadata"]["suggestion_id"] == suggestion_id


# --- POST /suggestions/:id/resolve ---

def test_resolve_suggestion_returns_200_and_resolved_at(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]
    r2 = resolve(client, sid, suggestion_id)
    assert r2.status_code == 200
    assert "resolved_at" in r2.get_json()


def test_resolve_nonexistent_suggestion_returns_404(client):
    sid = make_session(client)
    r = resolve(client, sid, "nonexistent-id")
    assert r.status_code == 404


def test_resolve_already_resolved_returns_409(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]
    resolve(client, sid, suggestion_id)
    r2 = resolve(client, sid, suggestion_id)
    assert r2.status_code == 409


def test_resolve_dual_writes_suggestion_resolved_event(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]
    resolve(client, sid, suggestion_id)
    events = get_events(client, sid)
    event_types = [e["event_type"] for e in events]
    assert "suggestion_resolved" in event_types


def test_resolve_suggestion_from_different_session_returns_404(client):
    sid1 = make_session(client)
    fid = make_file(client, sid1)
    iid = make_interaction(client, sid1)
    r = post_suggestion(client, sid1, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]

    sid2 = make_session(client)
    r2 = resolve(client, sid2, suggestion_id)
    assert r2.status_code == 404


def test_resolve_missing_final_content_returns_400(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]
    r2 = client.post(
        f"/api/v1/suggestions/{suggestion_id}/resolve",
        json={"all_accepted": True, "any_modified": False},
        headers={"X-Session-ID": sid},
    )
    assert r2.status_code == 400


# --- GET /suggestions/:id ---

def test_get_suggestion_returns_full_row(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]
    r2 = client.get(f"/api/v1/suggestions/{suggestion_id}", headers={"X-Session-ID": sid})
    assert r2.status_code == 200
    data = r2.get_json()
    assert data["suggestion_id"] == suggestion_id
    assert data["resolved_at"] is None
    assert data["all_accepted"] is None


def test_get_suggestion_after_resolve_shows_resolved_at(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    iid = make_interaction(client, sid)
    r = post_suggestion(client, sid, fid, iid)
    suggestion_id = r.get_json()["suggestion_id"]
    resolve(client, sid, suggestion_id, all_accepted=True)
    r2 = client.get(f"/api/v1/suggestions/{suggestion_id}", headers={"X-Session-ID": sid})
    data = r2.get_json()
    assert data["resolved_at"] is not None
    assert data["all_accepted"] is True


def test_get_nonexistent_suggestion_returns_404(client):
    sid = make_session(client)
    r = client.get("/api/v1/suggestions/does-not-exist", headers={"X-Session-ID": sid})
    assert r.status_code == 404
