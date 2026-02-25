import uuid
import json
from datetime import datetime, timezone
from base import Base
from db import engine
from schema import Event


def write_event(db, session_id, actor, event_type, content="", metadata=None):
    """
    Appends a new record to the session's event history.

    Args:
        db: SQLAlchemy database session.
        session_id: Unique identifier for the current assessment.
        actor: Entity performing the action (e.g., 'user', 'system').
        event_type: Category of action (e.g., 'execute', 'panel_focus').
        content: The primary text payload of the event.
        metadata: Optional dictionary of additional contextual attributes.

    Returns:
        The newly created Event instance.
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


def clear_database():
    """
    Wipes all data from the assessment database and recreates the schema.
    
    This is used for the 'Secret Login' reset mechanism to ensure a clean 
    state between candidate sessions during platform demonstrations.
    """
    import schema  # Ensure all models are registered with Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
