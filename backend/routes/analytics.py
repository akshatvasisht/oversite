import json
from flask import Blueprint, jsonify, request
from sqlalchemy import desc
from db import get_db
from models import Session, SessionScore, Event, AIInteraction, ChunkDecision
from scoring import trigger_scoring, extract_c1_features, FEATURE_NAMES

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/analytics/overview", methods=["GET"])
def get_overview():
    db = next(get_db())
    try:
        completed_only = request.args.get("completed_only", "false").lower() == "true"
        
        query = db.query(Session).order_by(desc(Session.started_at))
        if completed_only:
            query = query.filter(Session.ended_at != None)
            
        sessions = query.all()
        
        results = []
        for s in sessions:
            score = db.query(SessionScore).filter_by(session_id=s.session_id).first()
            
            results.append({
                "session_id": s.session_id,
                "username": s.username,
                "project_name": s.project_name,
                "status": "Submitted" if s.ended_at else "In Progress",
                "score": score.weighted_score if score else None,
                "label": score.overall_label if score else None,
                "date_submitted": s.ended_at.isoformat() if s.ended_at else None,
                "started_at": s.started_at.isoformat() if s.started_at else None,
            })
            
        return jsonify({"sessions": results}), 200
    finally:
        db.close()


@analytics_bp.route("/analytics/session/<session_id>", methods=["GET"])
def get_session_analytics(session_id):
    db = next(get_db())
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if not session:
            return jsonify({"error": "Session not found"}), 404

        # 1. Fetch cached scores if any
        score_record = db.query(SessionScore).filter_by(session_id=session_id).first()
        
        score_data = {
            "overall_label": None,
            "weighted_score": None,
            "structural_scores": None,
            "prompt_quality_scores": None,
            "review_scores": None,
            "llm_narrative": None,
            "fallback_components": None
        }
        
        if score_record:
            score_data = {
                "overall_label": score_record.overall_label,
                "weighted_score": score_record.weighted_score,
                "structural_scores": json.loads(score_record.structural_scores) if score_record.structural_scores else None,
                "prompt_quality_scores": json.loads(score_record.prompt_quality_scores) if score_record.prompt_quality_scores else None,
                "review_scores": json.loads(score_record.review_scores) if score_record.review_scores else None,
                "llm_narrative": score_record.llm_narrative,
                "fallback_components": json.loads(score_record.fallback_components) if score_record.fallback_components else []
            }

        # 2. Compute live metrics using the same feature extraction used in scoring
        features_array = extract_c1_features(session_id, db)
        live_metrics = {name: float(val) for name, val in zip(FEATURE_NAMES, features_array)}

        return jsonify({
            **score_data,
            **live_metrics,
            "session_id": session_id,
            "status": "Submitted" if session.ended_at else "In Progress"
        }), 200
    finally:
        db.close()


@analytics_bp.route("/analytics/session/<session_id>/score", methods=["POST"])
def force_score_session(session_id):
    db = next(get_db())
    try:
        session = db.query(Session).filter_by(session_id=session_id).first()
        if not session:
            return jsonify({"error": "Session not found"}), 404
            
        # Optional: check if session is ended or allow manual early scoring
        score_id = trigger_scoring(session_id, db)
        
        if score_id:
            return jsonify({"message": "Scoring triggered", "score_id": score_id}), 200
        else:
            return jsonify({"error": "Scoring pipeline failed"}), 500
    finally:
        db.close()
