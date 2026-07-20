"""File-system services with transactional CV deletion."""

import sqlite3
import uuid
from pathlib import Path

from repositories import RecruiterRepository


def safe_upload_path(upload_folder, filename):
    if not filename:
        return None
    directory = Path(upload_folder).resolve()
    candidate = (directory / filename).resolve()
    return candidate if candidate.parent == directory else None


def delete_cv_transaction(db, cv_id, upload_folder):
    repository = RecruiterRepository(db)
    cv = repository.find_cv_file(cv_id)
    if not cv:
        return False, False
    filepath = safe_upload_path(upload_folder, cv["file_path"])
    staged = None
    try:
        repository.begin_delete_cv(cv_id)
        if filepath and filepath.is_file():
            staged = filepath.with_name(f".deleting-{uuid.uuid4().hex}-{filepath.name}")
            filepath.replace(staged)
        repository.commit_delete_cv()
    except (OSError, sqlite3.Error):
        repository.rollback_delete_cv()
        if staged and staged.exists():
            staged.replace(filepath)
        raise
    if staged:
        try:
            staged.unlink()
        except OSError:
            return True, True
    return True, False
