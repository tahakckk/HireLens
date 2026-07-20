"""Operational health endpoints for deployment platforms."""

from importlib.util import find_spec

from flask import Blueprint, current_app, jsonify

from repositories import SystemRepository


health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@health_bp.get("/ready")
def ready():
    checks = {
        "database": SystemRepository().ping(),
        "nlp_service": "nlp_engine" in current_app.extensions,
        "cv_service": "extractive_cv_generator" in current_app.extensions,
        "spacy_model": find_spec(current_app.config["SPACY_MODEL"]) is not None,
    }
    is_ready = all(checks.values())
    return jsonify({
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }), 200 if is_ready else 503
