import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from schema import File, EditorEvent
from utils import write_event
from routes.session import require_session

files_bp = Blueprint("files", __name__)


@files_bp.route("/files", methods=["POST"])
@require_session
def create_file(session, db):
    """
    Creates a new file record for the current session.
    ---
    Input (JSON):
        - filename (str): Name of the file (e.g., 'utils.py')
        - initial_content (str, optional): Starting content
        - language (str, optional): Language identifier
    Output (201):
        - file_id (str): UUID of the created file
        - created_at (str): ISO timestamp
    Errors:
        - 400: Missing filename
    """
    data = request.get_json()
    filename = data.get("filename")
    initial_content = data.get("initial_content", "")
    language = data.get("language")

    if not filename:
        return jsonify({"error": "filename is required"}), 400

    file_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    db.add(File(
        file_id=file_id,
        session_id=session.session_id,
        filename=filename,
        language=language,
        created_at=now,
        initial_content=initial_content,
    ))

    write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="file_open",
        content=filename,
        metadata={"file_id": file_id, "filename": filename},
    )

    db.add(EditorEvent(
        event_id=str(uuid.uuid4()),
        session_id=session.session_id,
        file_id=file_id,
        trigger="open",
        content=initial_content,
        edit_delta=None,
        timestamp=now,
        char_count=len(initial_content),
    ))

    db.commit()

    return jsonify({
        "file_id": file_id,
        "created_at": now.isoformat(),
    }), 201


from services.diff import compute_edit_delta

@files_bp.route("/files/<file_id>/save", methods=["POST"])
@require_session
def save_file(session, db, file_id):
    """
    Saves a snapshot of a file's content and records an editor event.
    ---
    Input (Path):
        - file_id (str): UUID of the file to save
    Input (JSON):
        - content (str): The full content of the file
    Output (200):
        - event_id (str): UUID of the generated EditorEvent
        - saved_at (str): ISO timestamp
    Errors:
        - 400: Missing content
        - 404: File not found
    """
    data = request.get_json()
    content = data.get("content")

    if content is None:
        return jsonify({"error": "content is required"}), 400

    file = db.query(File).filter_by(file_id=file_id, session_id=session.session_id).first()
    if not file:
        return jsonify({"error": "File not found"}), 404

    # Diff against last snapshot
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
        trigger="save",
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
        metadata={"file_id": file_id, "trigger": "save"},
    )

    db.commit()

    return jsonify({
        "event_id": editor_ev.event_id,
        "saved_at": now.isoformat(),
    }), 200


@files_bp.route("/events/file", methods=["POST"])
@require_session
def file_event(session, db):
    """
    Logs metadata-only file events (open/close).
    ---
    Input (JSON):
        - file_id (str): UUID of the file
        - event_type (str): file_open or file_close
    Output (200):
        - event_id (str): UUID of the generated Event record
    Errors:
        - 400: Invalid event type
        - 404: File not found
    """
    data = request.get_json()
    file_id = data.get("file_id")
    event_type = data.get("event_type")

    valid_types = {"file_open", "file_close"}
    if event_type not in valid_types:
        return jsonify({"error": f"event_type must be one of {valid_types}"}), 400

    file = db.query(File).filter_by(file_id=file_id, session_id=session.session_id).first()
    if not file:
        return jsonify({"error": "File not found"}), 404

    event = write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type=event_type,
        content=file.filename,
        metadata={"file_id": file_id},
    )

    db.commit()

    return jsonify({"event_id": event.event_id}), 200
