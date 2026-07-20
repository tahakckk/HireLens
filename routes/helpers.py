"""Shared HTTP and upload helpers for the application blueprints."""
from pathlib import Path

from flask import current_app

from file_validation import validate_cv_file


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def get_upload_path(stored_filename):
    if not stored_filename:
        return None
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    candidate = (upload_dir / stored_filename).resolve()
    return candidate if candidate.parent == upload_dir else None


def remove_upload_file(filepath):
    try:
        if filepath and filepath.is_file():
            filepath.unlink()
    except OSError:
        current_app.logger.exception("Unable to remove temporary uploaded CV file")


def validate_saved_cv(filepath):
    try:
        is_valid = validate_cv_file(str(filepath))
    except OSError:
        current_app.logger.exception("Unable to validate uploaded CV file")
        is_valid = False
    if not is_valid:
        remove_upload_file(filepath)
    return is_valid
