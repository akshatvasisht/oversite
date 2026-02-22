import os
from typing import Any
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from db import init_db
from routes.session import session_bp
from routes.files import files_bp
from routes.ai import ai_bp
from routes.suggestions import suggestions_bp
from routes.events import events_bp
from routes.analytics import analytics_bp
from scoring import load_models

import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example'))

app = Flask(__name__)
CORS(app)

app.register_blueprint(session_bp, url_prefix="/api/v1")
app.register_blueprint(files_bp, url_prefix="/api/v1")
app.register_blueprint(ai_bp, url_prefix="/api/v1")
app.register_blueprint(suggestions_bp, url_prefix="/api/v1")
app.register_blueprint(events_bp, url_prefix="/api/v1")
app.register_blueprint(analytics_bp, url_prefix="/api/v1")

@app.route("/api/v1/health")
def health() -> Any:
    """Core health check endpoint."""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()  # Make sure tables are created on start (useful for local dev)
    load_models() # Warm up the model cache
    app.run(port=8000, debug=True)
