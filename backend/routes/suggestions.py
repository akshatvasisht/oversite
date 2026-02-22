import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from models import AISuggestion, EditorEvent
from utils import write_event
from routes.session import require_session

suggestions_bp = Blueprint("suggestions", __name__)


def _write_editor_snapshot(db, session_id, file_id, trigger, content, suggestion_id):
    snapshot = EditorEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        file_id=file_id,
        trigger=trigger,
        content=content,
        edit_delta=None,
        suggestion_id=suggestion_id,
        timestamp=datetime.now(timezone.utc),
        char_count=len(content),
    )
    db.add(snapshot)
    return snapshot


@suggestions_bp.route("/suggestions", methods=["POST"])
@require_session
def create_suggestion(session, db):
    data = request.get_json()
    interaction_id = data.get("interaction_id")
    file_id = data.get("file_id")
    original_content = data.get("original_content")
    proposed_content = data.get("proposed_content")

    if not interaction_id:
        return jsonify({"error": "interaction_id is required"}), 400
    if not file_id:
        return jsonify({"error": "file_id is required"}), 400
    if original_content is None or proposed_content is None:
        return jsonify({"error": "original_content and proposed_content are required"}), 400
    if original_content == proposed_content:
        return jsonify({"error": "proposed_content must differ from original_content"}), 400

    suggestion_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    db.add(AISuggestion(
        suggestion_id=suggestion_id,
        interaction_id=interaction_id,
        session_id=session.session_id,
        file_id=file_id,
        original_content=original_content,
        proposed_content=proposed_content,
        hunks_count=None,
        shown_at=now,
    ))

    _write_editor_snapshot(
        db,
        session_id=session.session_id,
        file_id=file_id,
        trigger="post_suggestion",
        content=original_content,
        suggestion_id=suggestion_id,
    )

    write_event(
        db,
        session_id=session.session_id,
        actor="system",
        event_type="suggestion_shown",
        content=suggestion_id,
        metadata={"suggestion_id": suggestion_id, "interaction_id": interaction_id, "file_id": file_id},
    )

    db.commit()

    return jsonify({
        "suggestion_id": suggestion_id,
        "shown_at": now.isoformat(),
        "original_content": original_content,
        "proposed_content": proposed_content,
    }), 201


@suggestions_bp.route("/suggestions/<suggestion_id>/resolve", methods=["POST"])
@require_session
def resolve_suggestion(session, db, suggestion_id):
    suggestion = db.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()

    if not suggestion or suggestion.session_id != session.session_id:
        return jsonify({"error": "Suggestion not found"}), 404

    if suggestion.resolved_at is not None:
        return jsonify({"error": "Suggestion already resolved"}), 409

    data = request.get_json()
    final_content = data.get("final_content")
    all_accepted = data.get("all_accepted")
    any_modified = data.get("any_modified")

    if final_content is None:
        return jsonify({"error": "final_content is required"}), 400

    now = datetime.now(timezone.utc)
    suggestion.resolved_at = now
    suggestion.all_accepted = all_accepted
    suggestion.any_modified = any_modified

    _write_editor_snapshot(
        db,
        session_id=session.session_id,
        file_id=suggestion.file_id,
        trigger="suggestion_resolved",
        content=final_content,
        suggestion_id=suggestion_id,
    )

    write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="suggestion_resolved",
        content=suggestion_id,
        metadata={
            "suggestion_id": suggestion_id,
            "all_accepted": all_accepted,
            "any_modified": any_modified,
        },
    )

    db.commit()

    return jsonify({"resolved_at": now.isoformat()}), 200


@suggestions_bp.route("/suggestions/<suggestion_id>", methods=["GET"])
@require_session
def get_suggestion(session, db, suggestion_id):
    suggestion = db.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()

    if not suggestion or suggestion.session_id != session.session_id:
        return jsonify({"error": "Suggestion not found"}), 404

    return jsonify({
        "suggestion_id": suggestion.suggestion_id,
        "interaction_id": suggestion.interaction_id,
        "session_id": suggestion.session_id,
        "file_id": suggestion.file_id,
        "original_content": suggestion.original_content,
        "proposed_content": suggestion.proposed_content,
        "hunks_count": suggestion.hunks_count,
        "shown_at": suggestion.shown_at.isoformat() if suggestion.shown_at else None,
        "resolved_at": suggestion.resolved_at.isoformat() if suggestion.resolved_at else None,
        "all_accepted": suggestion.all_accepted,
        "any_modified": suggestion.any_modified,
    }), 200
