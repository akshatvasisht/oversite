import uuid
import json
from datetime import datetime, timezone
from models import Event


def write_event(db, session_id, actor, event_type, content="", metadata=None):
    """
    Dual-write helper. Every loggable action calls this to append a row
    to the unified events log consumed by the model pipeline.
    """
    event = Event(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        actor=actor,
        event_type=event_type,
        content=content,
        metadata_=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    return event
