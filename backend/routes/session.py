import uuid
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from db import get_db
from schema import Session, Event, File, EditorEvent
from utils import write_event
from services.scoring import trigger_scoring
from services.problem import ProblemService
import os

session_bp = Blueprint("session", __name__)

# Initialize the discovery service pointing to the project-level problems directory
PROBLEMS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "problems")
problem_service = ProblemService(PROBLEMS_PATH)


def get_session_or_404(db, session_id):
    """
    Retrieves a session record by its unique identifier.

    Args:
        db: The active database session injected by the dependency or decorator.
        session_id: The UUID string representing the session to look up.

    Returns:
        The Session model instance if found, or None if no match exists.
    """
    return db.query(Session).filter_by(session_id=session_id).first()


def require_session(f):
    """
    Decorator that ensures a valid X-Session-ID header is present.

    Validates that the session exists in the database and is active.
    Passes initialized 'session' and 'db' objects to the wrapped function.

    Args:
        f: The route handler function to be protected.
    """
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return jsonify({"error": "Missing X-Session-ID header"}), 401
        db = next(get_db())
        session = get_session_or_404(db, session_id)
        if not session:
            db.close()
            return jsonify({"error": "Session not found"}), 404
        try:
            return f(*args, session=session, db=db, **kwargs)
        finally:
            db.close()
    return decorated


@session_bp.route("/session/start", methods=["POST"])
def start_session():
    """
    Initializes a new assessment session or rehydrates an active one.

    If the user has an existing, un-ended session for the specified project, 
    the endpoint returns the persisted state to allow for idempotent resumes.

    Returns:
        A tuple containing the JSON response and HTTP status code. The payload 
        includes session ID, file state, and timing synchronization benchmarks.
    """
    data = request.get_json()
    username = data.get("username")
    project_name = data.get("project_name")

    if not username:
        return jsonify({"error": "username is required"}), 400

    db = next(get_db())
    try:
        existing_session = (
            db.query(Session)
            .filter_by(username=username, project_name=project_name)
            .filter(Session.ended_at == None)
            .order_by(Session.started_at.desc())
            .first()
        )

        now = datetime.now(timezone.utc)

        # Always load initial files from the problems directory
        initial_files_raw = problem_service.get_problem_initial_files(project_name)
        
        if existing_session:
            files = db.query(File).filter_by(session_id=existing_session.session_id).all()
            # Map of filename -> content for persisted edits
            persisted_edits = {}
            for f in files:
                last_event = (
                    db.query(EditorEvent)
                    .filter_by(file_id=f.file_id)
                    .order_by(EditorEvent.timestamp.desc())
                    .first()
                )
                if last_event:
                    persisted_edits[f.filename] = last_event.content

            files_data = []
            for f_raw in initial_files_raw:
                filename = f_raw["filename"]
                files_data.append({
                    "fileId": f"init-{uuid.uuid4()}",
                    "filename": filename,
                    "language": "python",
                    "content": persisted_edits.get(filename, f_raw["content"]),
                    "persisted": filename in persisted_edits
                })

            description = problem_service.get_problem_description(project_name)
            metadata = problem_service.get_problem_metadata(project_name)
            duration = int((now - existing_session.started_at.replace(tzinfo=timezone.utc)).total_seconds())

            return jsonify({
                "session_id": existing_session.session_id,
                "started_at": existing_session.started_at.isoformat(),
                "elapsed_seconds": max(0, duration),
                "files": files_data,
                "description": description,
                "title": metadata.get("title", "Problem"),
                "difficulty": metadata.get("difficulty", "Medium"),
                "duration": metadata.get("duration", "N/A"),
                "rehydrated": True 
            }), 200

        session_id = str(uuid.uuid4())
        session = Session(
            session_id=session_id,
            username=username,
            project_name=project_name,
            started_at=now,
        )
        db.add(session)

        write_event(
            db,
            session_id=session_id,
            actor="user",
            event_type="panel_focus",
            content="orientation",
            metadata={"phase": "orientation"},
        )

        db.commit()

        initial_files = []
        for f in initial_files_raw:
            initial_files.append({
                "fileId": f"init-{uuid.uuid4()}",
                "filename": f["filename"],
                "language": "python", 
                "content": f["content"],
                "persisted": False
            })

        description = problem_service.get_problem_description(project_name)
        metadata = problem_service.get_problem_metadata(project_name)

        return jsonify({
            "session_id": session_id,
            "started_at": now.isoformat(),
            "elapsed_seconds": 0,
            "files": initial_files,
            "description": description,
            "title": metadata.get("title", "Problem"),
            "difficulty": metadata.get("difficulty", "Medium"),
            "duration": metadata.get("duration", "N/A"),
            "rehydrated": False
        }), 201
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@session_bp.route("/session/end", methods=["POST"])
@require_session
def end_session(session, db):
    """
    Finalizes the candidate's assessment and triggers the evaluation pipeline.

    Calculates the total session duration and initiates the background 
    machine learning scoring task.

    Args:
        session: Active session model instance to be finalized.
        db: Database session.

    Returns:
        A JSON summary of the finalized session including total duration.
    """
    if session.ended_at:
        return jsonify({"error": "Session already ended"}), 400

    now = datetime.now(timezone.utc)
    session.ended_at = now
    duration = int((now - session.started_at.replace(tzinfo=timezone.utc)).total_seconds())

    db.commit()

    # Trigger full scoring pipeline
    trigger_scoring(session.session_id, db)

    return jsonify({
        "session_id": session.session_id,
        "ended_at": now.isoformat(),
        "duration_seconds": duration,
    }), 200


@session_bp.route("/session/phase", methods=["PATCH"])
@require_session
def update_phase(session, db):
    """
    Tracks the candidate's progression through assessment phases.

    Args:
        phase: One of 'orientation', 'implementation', or 'verification'.

    Args:
        session: Active session model instance.
        db: Database session.

    Returns:
        A JSON confirmation of the updated state and current phase label.
    """
    data = request.get_json()
    phase = data.get("phase")
    if not phase:
        return jsonify({"error": "phase is required"}), 400

    # Log as panel_focus event to track time spent in phase
    write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="panel_focus",
        content=phase,
        metadata={"phase": phase},
    )

    db.commit()
    return jsonify({"message": "Phase updated", "phase": phase}), 200


@session_bp.route("/questions", methods=["GET"])
def get_questions():
    """
    Retrieves the catalog of available coding challenges.

    If a username is provided, also returns the completion status for 
    each challenge.

    Returns:
        A list of question metadata objects, including completion status if authenticated.
    """
    username = request.args.get("username")
    problems = problem_service.list_problems()
    
    if username:
        db = next(get_db())
        try:
            for p in problems:
                session = (
                    db.query(Session)
                    .filter_by(username=username, project_name=p["project_name"])
                    .order_by(Session.started_at.desc())
                    .first()
                )
                if session:
                    p["status"] = "submitted" if session.ended_at else "in progress"
                else:
                    p["status"] = "pending"
        finally:
            db.close()
    else:
        for p in problems:
            p["status"] = "pending"

    return jsonify(problems), 200



@session_bp.route("/session/<session_id>/trace", methods=["GET"])
def get_trace(session_id):
    """
    Retrieves the complete chronological action log for a session.

    This is an administrative endpoint used to review exact candidate behavior.

    Args:
        session_id: Unique identifier for the session to audit.

    Returns:
        A chronological list of all telemetry events logged for the session.
    """
    db = next(get_db())
    try:
        session = get_session_or_404(db, session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404

        events = (
            db.query(Event)
            .filter_by(session_id=session_id)
            .order_by(Event.timestamp.asc())
            .all()
        )

        events_list = []
        for e in events:
            events_list.append({
                "event_id": e.event_id,
                "session_id": e.session_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "actor": e.actor,
                "event_type": e.event_type,
                "content": e.content,
                "metadata": json.loads(e.metadata_) if e.metadata_ else None,
            })

        return jsonify({
            "session_id": session_id,
            "events": events_list,
        }), 200
    finally:
        db.close()
