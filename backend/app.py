import os
from typing import Any
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from db import init_db

import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example'))

app = Flask(__name__)
CORS(app)

@app.route("/api/v1/health")
def health() -> Any:
    """Core health check endpoint."""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()  # Make sure tables are created on start (useful for local dev)
    app.run(port=8000, debug=True)
