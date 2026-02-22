import schema
from datetime import datetime, timezone, timedelta

def start_session(client, username="alice", project_name="test"):
    return client.post("/api/v1/session/start", json={"username": username, "project_name": project_name})

def make_session(client, username="alice", project_name="test"):
    r = start_session(client, username, project_name)
    return r.get_json().get("session_id")

def post_file(client, sid, filename="solution.py", content="# start"):
    return client.post(
        "/api/v1/files",
        json={"filename": filename, "initial_content": content},
        headers={"X-Session-ID": sid},
    )

def make_file(client, sid, filename="solution.py", content="# start"):
    r = post_file(client, sid, filename, content)
    return r.get_json().get("file_id")

def post_interaction(client, sid, prompt="write binary search"):
    return client.post(
        "/api/v1/ai/chat",
        json={"prompt": prompt},
        headers={"X-Session-ID": sid},
    )

def make_interaction(client, sid, prompt="write binary search"):
    r = post_interaction(client, sid, prompt)
    return r.get_json().get("interaction_id")

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

def resolve_suggestion(client, sid, suggestion_id, final_content="def foo():\n    return 2\n", all_accepted=True, any_modified=False):
    return client.post(
        f"/api/v1/suggestions/{suggestion_id}/resolve",
        json={
            "final_content": final_content,
            "all_accepted": all_accepted,
            "any_modified": any_modified,
        },
        headers={"X-Session-ID": sid},
    )

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

def get_events(client, sid):
    return client.get(f"/api/v1/session/{sid}/trace").get_json().get("events", [])

def seed_rich_session(db, session_id):
    now = datetime.now(timezone.utc)
    s = schema.Session(
        session_id=session_id,
        username="testuser",
        started_at=now - timedelta(minutes=10)
    )
    db.add(s)
    db.add(schema.Event(
        event_id="e1", session_id=session_id, timestamp=now - timedelta(minutes=9),
        actor="user", event_type="panel_focus", content="orientation"
    ))
    db.add(schema.Event(
        event_id="e2", session_id=session_id, timestamp=now - timedelta(minutes=8),
        actor="user", event_type="edit", content="print('hello')"
    ))
    db.add(schema.Event(
        event_id="e3", session_id=session_id, timestamp=now - timedelta(minutes=7),
        actor="user", event_type="execute", content="python solution.py"
    ))
    db.add(schema.AIInteraction(
        interaction_id="ai1", session_id=session_id, phase="implementation",
        prompt="How do I implement two sum? `int[] result`", response="Here is the code...",
        shown_at=now - timedelta(minutes=6)
    ))
    db.add(schema.AISuggestion(
        suggestion_id="s1", interaction_id="ai1", session_id=session_id,
        original_content="old", proposed_content="new", hunks_count=1,
        shown_at=now - timedelta(minutes=6)
    ))
    db.add(schema.ChunkDecision(
        decision_id="d1", suggestion_id="s1", session_id=session_id,
        chunk_index=0, original_code="old", proposed_code="new",
        final_code="new_modified_longer", decision="modified", time_on_chunk_ms=5000
    ))
    db.commit()

def seed_complete_session(db, session_id):
    now = datetime.now(timezone.utc)
    s = schema.Session(
        session_id=session_id,
        username="pro-coder",
        started_at=now - timedelta(minutes=10)
    )
    db.add(s)
    db.add(schema.Event(
        event_id="e_p1", session_id=session_id, timestamp=now - timedelta(minutes=9),
        actor="user", event_type="edit", content="x = 1"
    ))
    db.add(schema.Event(
        event_id="e_p2", session_id=session_id, timestamp=now - timedelta(minutes=8),
        actor="user", event_type="execute", content="python"
    ))
    db.add(schema.AIInteraction(
        interaction_id="ai_p1", session_id=session_id, prompt="write sum",
        response="```python\ndef s(): pass\n```", shown_at=now - timedelta(minutes=7)
    ))
    db.add(schema.AISuggestion(
        suggestion_id="sug_p1", interaction_id="ai_p1", session_id=session_id,
        original_content="pass", proposed_content="return a+b", hunks_count=1
    ))
    db.add(schema.ChunkDecision(
        decision_id="dec_p1", suggestion_id="sug_p1", session_id=session_id,
        chunk_index=0, original_code="pass", proposed_code="return a+b",
        final_code="return sum(a, b)", decision="modified", time_on_chunk_ms=4000
    ))
    db.commit()
