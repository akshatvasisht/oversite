from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, JSON
from base import Base

class Session(Base):
    __tablename__ = 'sessions'
    id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    project_name = Column(String, nullable=False)
    final_phase = Column(String)
    started_at = Column(Integer)
    ended_at = Column(Integer)

class File(Base):
    __tablename__ = 'files'
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.id'), nullable=False)
    filename = Column(String, nullable=False)

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('sessions.id'), nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(Integer)

class AIInteraction(Base):
    __tablename__ = 'ai_interactions'
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.id'), nullable=False)
    file_id = Column(String, ForeignKey('files.id'))

class AISuggestion(Base):
    __tablename__ = 'ai_suggestions'
    id = Column(String, primary_key=True)
    interaction_id = Column(String, ForeignKey('ai_interactions.id'), nullable=False)
    shown_at = Column(Integer)

class ChunkDecision(Base):
    __tablename__ = 'chunk_decisions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    suggestion_id = Column(String, ForeignKey('ai_suggestions.id'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)
    final_code = Column(Text, nullable=False)

class EditorEvent(Base):
    __tablename__ = 'editor_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('sessions.id'), nullable=False)
    file_id = Column(String, ForeignKey('files.id'), nullable=False)

class SessionScore(Base):
    __tablename__ = 'session_scores'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey('sessions.id'), nullable=False)
    overall_label = Column(String)
    weighted_score = Column(Float)
    structural_scores = Column(JSON)
    prompt_quality_scores = Column(JSON)
    review_scores = Column(JSON)
    llm_narrative = Column(Text)
    fallback_components = Column(JSON)
