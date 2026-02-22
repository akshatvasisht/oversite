import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from schema import File, EditorEvent
from utils import write_event
from routes.session import require_session

events_bp = Blueprint("events", __name__)

VALID_PANELS = {"editor", "chat", "filetree", "orientation", "implementation", "verification"}


from services.diff import compute_edit_delta

@events_bp.route("/events/editor", methods=["POST"])
@require_session
def editor_event(session, db):
    data = request.get_json()
    file_id = data.get("file_id")
    content = data.get("content")

    if not file_id:
        return jsonify({"error": "file_id is required"}), 400
    if content is None:
        return jsonify({"error": "content is required"}), 400

    file = db.query(File).filter_by(file_id=file_id, session_id=session.session_id).first()
    if not file:
        return jsonify({"error": "File not found"}), 404

    last = (
        db.query(EditorEvent)
        .filter_by(file_id=file_id)
        .order_by(EditorEvent.timestamp.desc())
        .first()
    )
    previous_content = last.content if last else (file.initial_content or "")
    edit_delta = compute_edit_delta(previous_content, content)
    now = datetime.now(timezone.utc)

    editor_ev = EditorEvent(
        event_id=str(uuid.uuid4()),
        session_id=session.session_id,
        file_id=file_id,
        trigger="editor",
        content=content,
        edit_delta=edit_delta,
        timestamp=now,
        char_count=len(content),
    )
    db.add(editor_ev)

    write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="edit",
        content=edit_delta,
        metadata={"file_id": file_id, "trigger": "editor"},
    )

    db.commit()

    return jsonify({
        "event_id": editor_ev.event_id,
        "recorded_at": now.isoformat(),
    }), 201


@events_bp.route("/events/execute", methods=["POST"])
@require_session
def execute_event(session, db):
    data = request.get_json()
    exit_code = data.get("exit_code")
    output = data.get("output", "")
    file_id = data.get("file_id")

    if exit_code is None:
        return jsonify({"error": "exit_code is required"}), 400

    event = write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="execute",
        content=output,
        metadata={"exit_code": exit_code, "file_id": file_id},
    )

    db.commit()

    return jsonify({"event_id": event.event_id}), 201


@events_bp.route("/events/panel", methods=["POST"])
@require_session
def panel_event(session, db):
    data = request.get_json()
    panel = data.get("panel")

    if not panel:
        return jsonify({"error": "panel is required"}), 400
    if panel not in VALID_PANELS:
        return jsonify({"error": f"panel must be one of {sorted(VALID_PANELS)}"}), 400

    event = write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="panel_focus",
        content=panel,
        metadata={"panel": panel},
    )

    db.commit()

    return jsonify({"event_id": event.event_id}), 201
