"""SQLite connection and schema lifecycle helpers for HireLens."""

import sqlite3

from flask import current_app, g


SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS cvs (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL DEFAULT '',
        original_text TEXT,
        cleaned_text TEXT,
        extracted_skills TEXT,
        timeline TEXT,
        experience_months INTEGER DEFAULT 0,
        skill_recency TEXT,
        metadata TEXT,
        embedding BLOB,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        cleaned_description TEXT,
        required_skills TEXT,
        must_have_skills TEXT,
        nice_to_have_skills TEXT,
        embedding BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        cv_id TEXT NOT NULL,
        match_score REAL,
        matching_skills TEXT,
        semantic_matches TEXT,
        missing_skills TEXT,
        extra_skills TEXT,
        timeline_gaps TEXT,
        experience_score REAL,
        coverage_percent REAL,
        matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs (id),
        FOREIGN KEY (cv_id) REFERENCES cvs (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_profiles (
        id TEXT PRIMARY KEY,
        original_filename TEXT,
        original_text TEXT,
        profile_data TEXT,
        extracted_skills TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS job_search_sessions (
        id TEXT PRIMARY KEY,
        profile_id TEXT NOT NULL,
        job_url TEXT,
        job_data TEXT,
        optimized_cv TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
    )
    """,
)

LEGACY_COLUMNS = {
    "cvs": {
        "file_path": "TEXT NOT NULL DEFAULT ''",
        "timeline": "TEXT",
        "experience_months": "INTEGER DEFAULT 0",
        "skill_recency": "TEXT",
        "metadata": "TEXT",
    },
    "jobs": {
        "must_have_skills": "TEXT",
        "nice_to_have_skills": "TEXT",
    },
    "matches": {
        "timeline_gaps": "TEXT",
        "experience_score": "REAL",
        "semantic_matches": "TEXT",
        "text_similarity": "REAL",
        "penalty_applied": "REAL DEFAULT 0",
        "missing_must_haves": "TEXT",
        "format_score": "REAL DEFAULT 0",
        "keyword_score": "REAL DEFAULT 0",
        "section_score": "REAL DEFAULT 0",
        "language_match": "INTEGER DEFAULT 1",
        "sections_found": "TEXT",
        "cv_lang": "TEXT",
        "job_lang": "TEXT",
        "is_disqualified": "INTEGER DEFAULT 0",
        "is_pretty_resume": "INTEGER DEFAULT 0",
        "detail_metrics": "TEXT",
        "title_match_bonus": "REAL DEFAULT 0",
    },
}


def get_db():
    """Return the request/application-context SQLite connection."""
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        g.db = db
    return g.db


def close_db(_exception=None):
    """Close the SQLite connection at the end of an application context."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """Register database cleanup hooks on the existing Flask application."""
    app.teardown_appcontext(close_db)


def init_db():
    """Create current tables and add only missing columns from legacy schemas."""
    db = get_db()
    for statement in SCHEMA:
        db.execute(statement)

    for table, columns in LEGACY_COLUMNS.items():
        existing_columns = {
            row["name"] for row in db.execute(f"PRAGMA table_info({table})")
        }
        for column, definition in columns.items():
            if column not in existing_columns:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    db.commit()
