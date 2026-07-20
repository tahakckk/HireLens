
import numpy as np
from flask import current_app
from file_validation import validate_cv_file
from services import safe_upload_path


def nlp_engine():
    return current_app.extensions["nlp_engine"]


def extractive_cv_gen():
    return current_app.extensions["extractive_cv_gen"]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def get_upload_path(stored_filename):
    return safe_upload_path(current_app.config["UPLOAD_FOLDER"], stored_filename)


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


def embedding_to_bytes(embedding):
    return embedding.tobytes()


def bytes_to_embedding(data):
    return np.frombuffer(data, dtype=np.float32)
