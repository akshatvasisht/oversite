import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from schema import AIInteraction, Event
from utils import write_event
from routes.session import require_session
from services.llm import GeminiClient

ai_bp = Blueprint("ai", __name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert coding assistant helping a software engineer solve algorithmic "
    "programming challenges inside a technical interview environment. "
    "Be concise and direct. When suggesting code, produce complete, working implementations. "
    "Focus only on the problem at hand — do not add unsolicited explanations or caveats."
)

PHASE_VALUES = {"orientation", "implementation", "verification"}


def _current_phase(db, session_id: str):
    """Return the most recent interview phase from panel_focus events, or None."""
    event = (
        db.query(Event)
        .filter(
            Event.session_id == session_id,
            Event.event_type == "panel_focus",
            Event.content.in_(PHASE_VALUES),
        )
        .order_by(Event.timestamp.desc())
        .first()
    )
    return event.content if event else None


@ai_bp.route("/ai/chat", methods=["POST"])
@require_session
def chat(session, db):
    data = request.get_json()
    prompt_text = data.get("prompt")
    file_id = data.get("file_id")
    history = data.get("history", [])
    system_prompt = data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

    if not prompt_text:
        return jsonify({"error": "prompt is required"}), 400

    phase = _current_phase(db, session.session_id)

    # Call Gemini first — if it fails, write neither DB row
    try:
        client = GeminiClient()
        response_text = client.assistant_call(prompt_text, history, system_prompt)
    except Exception as e:
        return jsonify({"error": "AI service unavailable", "detail": str(e)}), 502

    interaction_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    has_code_changes = "```" in response_text

    db.add(AIInteraction(
        interaction_id=interaction_id,
        session_id=session.session_id,
        file_id=file_id,
        prompt=prompt_text,
        response=response_text,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        prompt_tokens=None,
        shown_at=now,
        phase=phase,
    ))

    write_event(
        db,
        session_id=session.session_id,
        actor="user",
        event_type="prompt",
        content=prompt_text,
        metadata={"interaction_id": interaction_id, "file_id": file_id, "phase": phase},
    )
    write_event(
        db,
        session_id=session.session_id,
        actor="ai",
        event_type="response",
        content=response_text,
        metadata={"interaction_id": interaction_id, "has_code_changes": has_code_changes},
    )

    db.commit()

    return jsonify({
        "interaction_id": interaction_id,
        "response": response_text,
        "has_code_changes": has_code_changes,
        "shown_at": now.isoformat(),
    }), 201
