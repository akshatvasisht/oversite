from flask import Blueprint, jsonify, request

api_bp = Blueprint('api', __name__)

@api_bp.route('/data')
def get_data():
    return jsonify({"status": "ok", "source": "billing_v1"})

@api_bp.route('/compute')
def run_compute():
    return jsonify({"status": "running", "task": "heavy_ops"})
