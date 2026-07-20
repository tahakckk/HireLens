"""Repository and file-deletion services used by route handlers."""
import sqlite3
import uuid
from pathlib import Path


class CVRepository:
    def __init__(self, db):
        self.db = db

    def find_file(self, cv_id):
        return self.db.execute('SELECT file_path, filename FROM cvs WHERE id = ?', (cv_id,)).fetchone()

    def delete_with_matches(self, cv_id):
        self.db.execute('DELETE FROM matches WHERE cv_id = ?', (cv_id,))
        self.db.execute('DELETE FROM cvs WHERE id = ?', (cv_id,))


class JobRepository:
    def __init__(self, db):
        self.db = db

    def delete_with_matches(self, job_id):
        self.db.execute('DELETE FROM matches WHERE job_id = ?', (job_id,))
        self.db.execute('DELETE FROM jobs WHERE id = ?', (job_id,))


class MatchRepository:
    def __init__(self, db):
        self.db = db

    def delete_for_job(self, job_id):
        self.db.execute('DELETE FROM matches WHERE job_id = ?', (job_id,))

    def delete_for_cv(self, cv_id):
        self.db.execute('DELETE FROM matches WHERE cv_id = ?', (cv_id,))


class JobSearchRepository:
    def __init__(self, db):
        self.db = db

    def delete_session(self, session_id):
        self.db.execute('DELETE FROM job_search_sessions WHERE id = ?', (session_id,))

    def delete_profile(self, profile_id):
        self.db.execute('DELETE FROM job_search_sessions WHERE profile_id = ?', (profile_id,))
        self.db.execute('DELETE FROM user_profiles WHERE id = ?', (profile_id,))


def safe_upload_path(upload_folder, filename):
    if not filename:
        return None
    directory = Path(upload_folder).resolve()
    candidate = (directory / filename).resolve()
    return candidate if candidate.parent == directory else None


def delete_cv_transaction(db, cv_id, upload_folder):
    cv = CVRepository(db).find_file(cv_id)
    if not cv:
        return False, False
    filepath = safe_upload_path(upload_folder, cv['file_path'])
    staged = None
    try:
        db.execute('BEGIN')
        CVRepository(db).delete_with_matches(cv_id)
        if filepath and filepath.is_file():
            staged = filepath.with_name(f'.deleting-{uuid.uuid4().hex}-{filepath.name}')
            filepath.replace(staged)
        db.commit()
    except (OSError, sqlite3.Error):
        db.rollback()
        if staged and staged.exists():
            staged.replace(filepath)
        raise
    if staged:
        try:
            staged.unlink()
        except OSError:
            return True, True
    return True, False
