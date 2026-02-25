import os
import uuid
import tempfile
import subprocess
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
    """
    Records an incremental code modification event from the editor.

    Calculates the diff between the previous state and the current content
    to track candidate deliberation and iteration speed.

    Args:
        session: Active session model instance (injected).
        db: Database session (injected).

    Returns:
        A tuple containing the JSON record with event ID and HTTP status.
    """
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
    """
    Executes the specified entrypoint within an ephemeral sandbox environment.

    Provisioning a temporary directory, writes all session files, and 
    invokes the appropriate execution engine (python or pytest).

    Args:
        session: Active session model instance (injected).
        db: Database session (injected).

    Returns:
        A tuple containing the execution output (stdout/stderr) and exit status.
    """
    data = request.get_json()
    entrypoint = data.get("entrypoint")
    files = data.get("files", [])

    if not entrypoint or not files:
        return jsonify({"error": "entrypoint and files are required"}), 400

    event = write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="execute",
        content=entrypoint,
        metadata={"entrypoint": entrypoint},
    )
    db.commit()

    stdout_str = ""
    stderr_str = ""
    exit_code = 1

    try:
        # Dynamically provision an ephemeral directory for the sandbox execution
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in files:
                fname = f.get("filename")
                content = f.get("content", "")
                if fname:
                    filepath = os.path.join(tmpdir, fname)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "w") as out:
                        out.write(content)

            # Determine the appropriate execution engine based on file naming conventions
            # Support both specific test files and test directories
            is_dir = os.path.isdir(os.path.join(tmpdir, entrypoint))
            is_test_file = os.path.basename(entrypoint).startswith("test_") or os.path.basename(entrypoint).endswith("_test.py")
            
            import sys
            if is_dir:
                # If a directory is provided, check if it looks like a test suite
                has_tests = any(f.startswith("test_") or f.endswith("_test.py") for f in os.listdir(os.path.join(tmpdir, entrypoint)))
                if has_tests or entrypoint == "tests":
                    cmd = [sys.executable, "-m", "pytest", entrypoint, "-v"]
                else:
                    # Fallback to python execution if it's just a folder with no obvious tests
                    cmd = [sys.executable, entrypoint]
            elif is_test_file:
                cmd = [sys.executable, "-m", "pytest", entrypoint, "-v"]
            else:
                target_file = os.path.join(tmpdir, entrypoint)
                cmd = [sys.executable, target_file]

            result = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30
            )

            stdout_str = result.stdout
            stderr_str = result.stderr
            exit_code = result.returncode

    except subprocess.TimeoutExpired:
        stderr_str = "Execution timed out (10s limit)."
    except Exception as e:
        stderr_str = f"Execution engine error: {str(e)}"

    return jsonify({
        "status": "success",
        "event_id": event.event_id,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "exit_code": exit_code
    }), 200


@events_bp.route("/events/panel", methods=["POST"])
@require_session
def panel_event(session, db):
    """
    Logs a UI interaction event, such as a panel focus or phase change.

    Used to track time-on-task and workspace organization patterns.

    Args:
        session: Active session model instance (injected).
        db: Database session (injected).

    Returns:
        A tuple containing the uniquely generated event ID confirmation.
    """
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
