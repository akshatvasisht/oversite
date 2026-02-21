from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime
from db import Base

class Session(Base):
    __tablename__ = 'sessions'
    session_id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    project_name = Column(String)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    phase = Column(String)


class File(Base):
    __tablename__ = 'files'
    file_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    filename = Column(String, nullable=False)
    language = Column(String)
    created_at = Column(DateTime)
    initial_content = Column(Text)


class Event(Base):
    __tablename__ = 'events'
    event_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    actor = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    content = Column(Text)
    metadata_ = Column('metadata', Text)


class AIInteraction(Base):
    __tablename__ = 'ai_interactions'
    interaction_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    file_id = Column(String, ForeignKey('files.file_id'))
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model = Column(String)
    prompt_tokens = Column(Integer)
    shown_at = Column(DateTime)
    phase = Column(String)


class AISuggestion(Base):
    __tablename__ = 'ai_suggestions'
    suggestion_id = Column(String, primary_key=True)
    interaction_id = Column(String, ForeignKey('ai_interactions.interaction_id'), nullable=False)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    file_id = Column(String, ForeignKey('files.file_id'))
    original_content = Column(Text, nullable=False)
    proposed_content = Column(Text, nullable=False)
    hunks_count = Column(Integer)
    shown_at = Column(DateTime)
    resolved_at = Column(DateTime)
    all_accepted = Column(Boolean)
    any_modified = Column(Boolean)


class ChunkDecision(Base):
    __tablename__ = 'chunk_decisions'
    decision_id = Column(String, primary_key=True)
    suggestion_id = Column(String, ForeignKey('ai_suggestions.suggestion_id'), nullable=False)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    file_id = Column(String, ForeignKey('files.file_id'))
    chunk_index = Column(Integer, nullable=False)
    original_code = Column(Text, nullable=False)
    proposed_code = Column(Text, nullable=False)
    final_code = Column(Text, nullable=False)
    decision = Column(String, nullable=False)
    decided_at = Column(DateTime)
    time_on_chunk_ms = Column(Integer)
    chunk_start_line = Column(Integer)
    char_count_proposed = Column(Integer)


class EditorEvent(Base):
    __tablename__ = 'editor_events'
    event_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    file_id = Column(String, ForeignKey('files.file_id'), nullable=False)
    trigger = Column(String)
    content = Column(Text, nullable=False)
    edit_delta = Column(Text)
    suggestion_id = Column(String, ForeignKey('ai_suggestions.suggestion_id'))
    cursor_line = Column(Integer)
    cursor_col = Column(Integer)
    timestamp = Column(DateTime)
    char_count = Column(Integer)


class SessionScore(Base):
    __tablename__ = 'session_scores'
    score_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('sessions.session_id'), nullable=False)
    computed_at = Column(DateTime)
    structural_scores = Column(Text)
    prompt_quality_scores = Column(Text)
    review_scores = Column(Text)
    overall_label = Column(String)
    weighted_score = Column(Float)
    feature_importances = Column(Text)
    fallback_components = Column(Text)
    llm_narrative = Column(Text)
    judge_chain_of_thought = Column(Text)
