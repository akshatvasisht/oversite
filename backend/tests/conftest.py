import pytest
import os
from unittest.mock import patch, MagicMock
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from base import Base
from routes.session import session_bp
from routes.files import files_bp
from routes.ai import ai_bp
from routes.suggestions import suggestions_bp
from routes.events import events_bp
import models

@pytest.fixture(autouse=True)
def _stub_gemini():
    """Mock GeminiClient globally for backend tests so no real API calls are made."""
    mock_client = MagicMock()
    # Default mock response - individual tests can override this via mocking again or using the fixture
    mock_client.assistant_call.return_value = "Here is a solution:\n```python\nreturn 42\n```"
    mock_client.judge_call.return_value = "Candidate shows balanced reliance on AI tools."
    
    with patch("routes.ai.GeminiClient", return_value=mock_client), \
         patch("scoring.GeminiClient", return_value=mock_client):
        yield mock_client

@pytest.fixture
def engine():
    """In-memory SQLite DB for fast testing."""
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)

@pytest.fixture
def db_session(engine):
    """Provides a transactional database session."""
    TestSession = sessionmaker(bind=engine)
    s = TestSession()
    try:
        yield s
    finally:
        s.close()

@pytest.fixture
def app(engine):
    """Provides a pre-configured Flask app with all blueprints and mocked db."""
    TestSession = sessionmaker(bind=engine)

    def mock_get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    flask_app = Flask(__name__)
    flask_app.register_blueprint(session_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(files_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(ai_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(suggestions_bp, url_prefix="/api/v1")
    flask_app.register_blueprint(events_bp, url_prefix="/api/v1")
    flask_app.config["TESTING"] = True

    with patch("routes.session.get_db", mock_get_db), \
         patch("db.SessionLocal", TestSession), \
         patch("db.get_db", mock_get_db):
        yield flask_app

@pytest.fixture
def client(app):
    """Provides a Flask test client."""
    return app.test_client()
