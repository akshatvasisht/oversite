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
    "Be concise and direct. Focus only on the problem at hand. "
    "CRITICAL: When suggesting code changes, you MUST output the ENTIRE file completely "
    "from top to bottom. Do NOT use placeholders like `...` or omit any unchanged code. "
    "Your code block will be diffed against the original file, so missing lines will be interpreted as deletions."
)

PHASE_VALUES = {"orientation", "implementation", "verification"}


def _current_phase(db, session_id: str):
    """
    Identifies the candidate's active state from the session event log.

    Args:
        db: Database session.
        session_id: Unique session identifier.

    Returns:
        The label of the most recent phase (e.g., 'implementation'), or None.
    """
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
    """
    Facilitates multi-turn interaction with the technical assessment assistant.

    Records the conversation history and timestamps as telemetry for 
    behavioral analysis. Pre-pends relevant file context to ensure AI 
    suggestions are grounded in the active workspace.

    Returns:
        A JSON response containing the interaction ID and AI's response text.
    """
    data = request.get_json()
    prompt_text = data.get("prompt")
    file_id = data.get("file_id")
    history = data.get("history", [])
    system_prompt = data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    context = data.get("context", "")

    if not prompt_text:
        return jsonify({"error": "prompt is required"}), 400

    phase = _current_phase(db, session.session_id)

    # Prepend file context to the user prompt so Gemini can see the code
    full_prompt = f"{context}\n\n{prompt_text}" if context else prompt_text

    # Prioritize external LLM inference; only persist to the database upon 
    # successful reception of a model response to maintain data integrity.
    try:
        client = GeminiClient()
        response_text = client.assistant_call(full_prompt, history, system_prompt)
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
@ai_bp.route("/ai/history", methods=["GET"])
@require_session
def get_chat_history(session, db):
    """
    Retrieves the chronological record of AI interactions for the current session.

    Returns:
        A JSON object containing the list of historical chat messages.
    """
    interactions = (
        db.query(AIInteraction)
        .filter(AIInteraction.session_id == session.session_id)
        .order_by(AIInteraction.shown_at.asc())
        .all()
    )

    history = []
    for inter in interactions:
        history.append({
            "id": f"msg-hist-{inter.interaction_id[:8]}",
            "role": "user",
            "content": inter.prompt,
            "timestamp": inter.shown_at.isoformat() if inter.shown_at else None
        })
        history.append({
            "id": f"msg-hist-{inter.interaction_id[:8]}-res",
            "role": "ai",
            "content": inter.response,
            "timestamp": inter.shown_at.isoformat() if inter.shown_at else None
        })

    return jsonify({"messages": history}), 200
