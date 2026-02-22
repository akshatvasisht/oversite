from flask import Blueprint, request, jsonify
from functools import wraps

auth_bp = Blueprint("auth", __name__)

TEST_USERS = {
    "candidate1": "password123",
    "admin1": "admin123"
}

ROLES = {
    "candidate1": "candidate",
    "admin1": "admin"
}

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if username in TEST_USERS and TEST_USERS[username] == password:
        role = ROLES[username]
        # In a real app we'd create a JWT and set it in a secure HTTP-Only cookie. 
        # Here we just return a simple structured mock token.
        return jsonify({
            "userId": username,
            "role": role,
            "token": f"mock-jwt-{role}-{username}"
        }), 200

    return jsonify({"error": "Invalid credentials"}), 401

def require_role(role_required):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
                
            token = auth_header.split(" ")[1]
            if not token.startswith(f"mock-jwt-{role_required}"):
                return jsonify({"error": "Insufficient permissions"}), 403
                
            return f(*args, **kwargs)
        return decorated
    return decorator
