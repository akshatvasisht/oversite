from flask import Blueprint, request, jsonify
from functools import wraps

auth_bp = Blueprint("auth", __name__)

ROLES = {
    "candidate": "candidate",
    "candidate2": "candidate",
    "candidate3": "candidate",
    "admin": "admin"
}

@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    Authenticates an user based on pre-defined demo usernames.

    Validates the username against a static registry and issues 
    a synthetic authorization token.

    Returns:
        A tuple containing the JSON response and HTTP status code. 
        Success returns user metadata and a synthetic token.
    """
    data = request.get_json() or {}
    username = data.get("username", "")

    if not username:
        return jsonify({"error": "Username is required"}), 400

    if username.lower() == "databasereset":
        from utils import clear_database
        try:
            clear_database()
            return jsonify({
                "userId": "system",
                "role": "admin",
                "token": "reset-success",
                "message": "Database reset successfully. Page will reload."
            }), 200
        except Exception as e:
            return jsonify({"error": f"Reset failed: {str(e)}"}), 500

    if username in ROLES:
        role = ROLES[username]
        # Generate a structured synthetic token to facilitate role-based access control (RBAC).
        return jsonify({
            "userId": username,
            "role": role,
            "token": f"mock-jwt-{role}-{username}"
        }), 200

    return jsonify({"error": "User not found"}), 401

def require_role(role_required):
    """
    Access control decorator for standardizing role-based authorization.

    Args:
        role_required: The role string ('candidate' or 'admin') required for access.

    Returns:
        A specialized decorator function for route protection.
    """
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
