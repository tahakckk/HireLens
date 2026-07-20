"""SQLite lifecycle and idempotent schema migrations."""
import sqlite3
from flask import current_app, g

SCHEMA = (
'''CREATE TABLE IF NOT EXISTS cvs (id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_path TEXT NOT NULL DEFAULT '', original_text TEXT, cleaned_text TEXT, extracted_skills TEXT, timeline TEXT, experience_months INTEGER DEFAULT 0, skill_recency TEXT, metadata TEXT, embedding BLOB, uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
'''CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, cleaned_description TEXT, required_skills TEXT, must_have_skills TEXT, nice_to_have_skills TEXT, embedding BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
'''CREATE TABLE IF NOT EXISTS matches (id TEXT PRIMARY KEY, job_id TEXT NOT NULL, cv_id TEXT NOT NULL, match_score REAL, matching_skills TEXT, semantic_matches TEXT, missing_skills TEXT, extra_skills TEXT, timeline_gaps TEXT, experience_score REAL, coverage_percent REAL, matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (job_id) REFERENCES jobs (id), FOREIGN KEY (cv_id) REFERENCES cvs (id))''',
'''CREATE TABLE IF NOT EXISTS user_profiles (id TEXT PRIMARY KEY, original_filename TEXT, original_text TEXT, profile_data TEXT, extracted_skills TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
'''CREATE TABLE IF NOT EXISTS job_search_sessions (id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, job_url TEXT, job_data TEXT, optimized_cv TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (profile_id) REFERENCES user_profiles(id))''',
)
MIGRATIONS = {
    'cvs': [('file_path', "TEXT NOT NULL DEFAULT ''"), ('timeline', 'TEXT'), ('experience_months', 'INTEGER DEFAULT 0'), ('skill_recency', 'TEXT'), ('metadata', 'TEXT')],
    'jobs': [('must_have_skills', 'TEXT'), ('nice_to_have_skills', 'TEXT')],
    'matches': [('timeline_gaps', 'TEXT'), ('experience_score', 'REAL'), ('semantic_matches', 'TEXT'), ('text_similarity', 'REAL'), ('penalty_applied', 'REAL DEFAULT 0'), ('missing_must_haves', 'TEXT'), ('format_score', 'REAL DEFAULT 0'), ('keyword_score', 'REAL DEFAULT 0'), ('section_score', 'REAL DEFAULT 0'), ('language_match', 'INTEGER DEFAULT 1'), ('sections_found', 'TEXT'), ('cv_lang', 'TEXT'), ('job_lang', 'TEXT'), ('is_disqualified', 'INTEGER DEFAULT 0'), ('is_pretty_resume', 'INTEGER DEFAULT 0'), ('detail_metrics', 'TEXT'), ('title_match_bonus', 'REAL DEFAULT 0')],
}

def _configure(connection):
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA journal_mode=WAL')
    return connection

def get_db():
    if 'db' not in g:
        g.db = _configure(sqlite3.connect(current_app.config['DATABASE']))
    return g.db

def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Create and upgrade schema without changing existing data."""
    db = _configure(sqlite3.connect(current_app.config['DATABASE']))
    try:
        for statement in SCHEMA:
            db.execute(statement)
        for table, columns in MIGRATIONS.items():
            existing = {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}
            for name, definition in columns:
                if name not in existing:
                    db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
        db.commit()
    finally:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
