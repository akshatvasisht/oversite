import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from schema import AISuggestion, EditorEvent
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


@suggestions_bp.route("/suggestions/<suggestion_id>/chunks/<int:chunk_index>/decide", methods=["POST"])
@require_session
def decide_chunk(session, db, suggestion_id, chunk_index):
    from schema import ChunkDecision
    
    suggestion = db.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()
    if not suggestion or suggestion.session_id != session.session_id:
        return jsonify({"error": "Suggestion not found"}), 404

    # Validate chunk_index (assuming 0-indexed up to hunks_count - 1)
    if suggestion.hunks_count is not None and (chunk_index < 0 or chunk_index >= suggestion.hunks_count):
        return jsonify({"error": "Invalid chunk_index for this suggestion"}), 400

    # Check if already decided
    existing = db.query(ChunkDecision).filter_by(suggestion_id=suggestion_id, chunk_index=chunk_index).first()
    if existing:
        return jsonify({"error": "Chunk already decided"}), 409

    data = request.get_json()
    decision = data.get("decision")
    final_code = data.get("final_code")
    time_ms = data.get("time_on_chunk_ms")

    if decision not in ["accepted", "rejected", "modified"]:
        return jsonify({"error": "Invalid decision"}), 400
    if final_code is None:
        return jsonify({"error": "final_code is required"}), 400
    if time_ms is None or not isinstance(time_ms, int):
        return jsonify({"error": "time_on_chunk_ms must be an integer"}), 400

    time_on_chunk_ms = max(100, min(300000, time_ms))
    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    try:
        chunk_decision = ChunkDecision(
            decision_id=decision_id,
            suggestion_id=suggestion_id,
            session_id=session.session_id,
            file_id=suggestion.file_id,
            chunk_index=chunk_index,
            original_code="", # Optional, not provided in body typically, but schema requires it. We'll set empty string if unset.
            proposed_code="", # Optional
            final_code=final_code,
            decision=decision,
            time_on_chunk_ms=time_on_chunk_ms,
        )
        db.add(chunk_decision)

        write_event(
            db,
            session_id=session.session_id,
            actor="user",
            event_type=f"chunk_{decision}",
            content=final_code,
            metadata={
                "suggestion_id": suggestion_id,
                "chunk_index": chunk_index,
                "time_on_chunk_ms": time_on_chunk_ms
            },
        )

        current_decisions_count = db.query(ChunkDecision).filter_by(suggestion_id=suggestion_id).count()
        if suggestion.hunks_count is not None and (current_decisions_count) == suggestion.hunks_count:
            suggestion.resolved_at = now
            all_decisions = db.query(ChunkDecision).filter_by(suggestion_id=suggestion_id).all()
            suggestion.all_accepted = all(d.decision == "accepted" for d in all_decisions)
            suggestion.any_modified = any(d.decision == "modified" for d in all_decisions)

        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Transaction failed", "details": str(e)}), 500

    return jsonify({
        "decision_id": decision_id,
        "decided_at": now.isoformat()
    }), 201
