import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from db import init_db

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__dirname), '.env.example')) # or .env

app = Flask(__name__)
# Enable CORS
CORS(app)

# Blueprint stubs
@app.route("/api/v1/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()  # Make sure tables are created on start (useful for local dev)
    app.run(port=8000, debug=True)
