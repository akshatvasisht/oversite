import uuid
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from db import get_db
from schema import Session, Event
from utils import write_event
from services.scoring import trigger_scoring

session_bp = Blueprint("session", __name__)


def get_session_or_404(db, session_id):
    session = db.query(Session).filter_by(session_id=session_id).first()
    if not session:
        return None
    return session


def require_session(f):
    """Decorator that extracts and validates X-Session-ID header."""
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
    data = request.get_json()
    username = data.get("username")
    project_name = data.get("project_name")

    if not username:
        return jsonify({"error": "username is required"}), 400

    db = next(get_db())
    try:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

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

        return jsonify({
            "session_id": session_id,
            "started_at": now.isoformat(),
        }), 201
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@session_bp.route("/session/end", methods=["POST"])
@require_session
def end_session(session, db):
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



@session_bp.route("/session/<session_id>/trace", methods=["GET"])
def get_trace(session_id):
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
