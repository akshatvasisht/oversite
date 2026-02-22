from helpers import make_session, make_file, get_events

def chat(client, sid, prompt="explain this", file_id=None):
    body = {"prompt": prompt}
    if file_id:
        body["file_id"] = file_id
    return client.post("/api/v1/ai/chat", json=body, headers={"X-Session-ID": sid})

# --- POST /ai/chat ---

def test_chat_returns_expected_fields(client):
    sid = make_session(client)
    r = chat(client, sid)
    assert r.status_code == 201
    data = r.get_json()
    assert "interaction_id" in data
    assert "response" in data
    assert "has_code_changes" in data
    assert "shown_at" in data


def test_chat_has_code_changes_true_when_backticks_in_response(client):
    sid = make_session(client)
    r = chat(client, sid)
    assert r.get_json()["has_code_changes"] is True


def test_chat_has_code_changes_false_when_no_backticks(_stub_gemini, client):
    _stub_gemini.assistant_call.return_value = "Just some plain text, no code."
    sid = make_session(client)
    r = chat(client, sid)
    assert r.get_json()["has_code_changes"] is False


def test_chat_dual_writes_prompt_and_response_events(client):
    sid = make_session(client)
    chat(client, sid, prompt="how do I do this?")
    events = get_events(client, sid)
    event_types = [e["event_type"] for e in events]
    assert "prompt" in event_types
    assert "response" in event_types


def test_chat_prompt_event_content_matches_prompt(client):
    sid = make_session(client)
    chat(client, sid, prompt="write a binary search")
    events = get_events(client, sid)
    prompt_event = next(e for e in events if e["event_type"] == "prompt")
    assert prompt_event["content"] == "write a binary search"
    assert prompt_event["actor"] == "user"


def test_chat_response_event_actor_is_ai(client):
    sid = make_session(client)
    chat(client, sid)
    events = get_events(client, sid)
    response_event = next(e for e in events if e["event_type"] == "response")
    assert response_event["actor"] == "ai"


def test_chat_missing_prompt_returns_400(client):
    sid = make_session(client)
    r = client.post("/api/v1/ai/chat", json={}, headers={"X-Session-ID": sid})
    assert r.status_code == 400


def test_chat_missing_session_header_returns_401(client):
    r = client.post("/api/v1/ai/chat", json={"prompt": "hello"})
    assert r.status_code == 401


def test_chat_gemini_failure_returns_502_and_writes_no_rows(_stub_gemini, client):
    _stub_gemini.assistant_call.side_effect = Exception("API error")
    sid = make_session(client)
    r = chat(client, sid)
    assert r.status_code == 502
    # No prompt or response events written
    events = get_events(client, sid)
    event_types = [e["event_type"] for e in events]
    assert "prompt" not in event_types
    assert "response" not in event_types


def test_chat_with_file_id_stored(client):
    sid = make_session(client)
    fid = make_file(client, sid)
    r = chat(client, sid, file_id=fid)
    assert r.status_code == 201


def test_chat_phase_captured_from_panel_focus(client):
    """Phase on the interaction should reflect the most recent panel_focus phase event."""
    sid = make_session(client)
    # orientation panel_focus is already written by session start
    r = chat(client, sid, prompt="hello")
    assert r.status_code == 201
    # Verify prompt event metadata includes phase
    events = get_events(client, sid)
    prompt_event = next(e for e in events if e["event_type"] == "prompt")
    assert prompt_event["metadata"]["phase"] == "orientation"
