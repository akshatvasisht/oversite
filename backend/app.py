import os
import logging
from typing import Any
from dotenv import load_dotenv

# Initialize environment configuration from local or project-level .env files
dotenv_paths = [
    os.path.join(os.path.dirname(__file__), '.env'),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example')
]

for path in dotenv_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

from flask import Flask, jsonify
from flask_cors import CORS
from db import init_db
from routes.session import session_bp
from routes.files import files_bp
from routes.ai import ai_bp
from routes.suggestions import suggestions_bp
from routes.events import events_bp
from routes.analytics import analytics_bp
from routes.auth import auth_bp
from services.scoring import load_models

# Configure high-level logging defaults for the backend application
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.register_blueprint(session_bp, url_prefix="/api/v1")
app.register_blueprint(files_bp, url_prefix="/api/v1")
app.register_blueprint(ai_bp, url_prefix="/api/v1")
app.register_blueprint(suggestions_bp, url_prefix="/api/v1")
app.register_blueprint(events_bp, url_prefix="/api/v1")
app.register_blueprint(analytics_bp, url_prefix="/api/v1")
app.register_blueprint(auth_bp, url_prefix="/api/v1")

@app.route("/api/v1/health")
def health() -> Any:
    """
    Verifies the operational status of the Flask application.

    Returns:
        A JSON response indicating the service is healthy.
    """
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    # Ensure the database schema is initialized before accepting requests
    init_db()
    
    # Pre-load ML artifacts to minimize cold-start latency for the first score request
    models = load_models()
    if not models and os.environ.get("SCORING_FALLBACK_MODE", "true").lower() != "true":
        raise RuntimeError("Model artifacts are required but failed to load. Set SCORING_FALLBACK_MODE=true to bypass.")
        
    app.run(port=8000, debug=True)
