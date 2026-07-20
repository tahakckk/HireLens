import sqlite3

import pytest
from flask import Flask

from database import get_db, init_app, init_db


def create_app(database_path):
    app = Flask(__name__)
    app.config.update(DATABASE=str(database_path))
    init_app(app)
    return app


def test_init_db_is_idempotent_and_enables_connection_pragmas(tmp_path):
    app = create_app(tmp_path / "hirelens.db")

    with app.app_context():
        init_db()
        init_db()
        db = get_db()

        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert isinstance(db.execute("SELECT 1").fetchone(), sqlite3.Row)

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO matches (id, job_id, cv_id) VALUES (?, ?, ?)",
                ("match-1", "unknown-job", "unknown-cv"),
            )


def test_init_db_adds_missing_legacy_columns_without_losing_data(tmp_path):
    database_path = tmp_path / "legacy.db"
    legacy_db = sqlite3.connect(database_path)
    legacy_db.execute(
        "CREATE TABLE cvs (id TEXT PRIMARY KEY, filename TEXT NOT NULL)"
    )
    legacy_db.execute(
        "INSERT INTO cvs (id, filename) VALUES (?, ?)",
        ("cv-1", "legacy.pdf"),
    )
    legacy_db.commit()
    legacy_db.close()

    app = create_app(database_path)
    with app.app_context():
        init_db()
        db = get_db()
        columns = {row["name"] for row in db.execute("PRAGMA table_info(cvs)")}

        assert {"file_path", "timeline", "experience_months", "metadata"} <= columns
        assert db.execute("SELECT filename FROM cvs WHERE id = ?", ("cv-1",)).fetchone()[0] == "legacy.pdf"


def test_application_context_closes_database_connection(tmp_path):
    app = create_app(tmp_path / "hirelens.db")

    with app.app_context():
        db = get_db()
        init_db()

    with pytest.raises(sqlite3.ProgrammingError):
        db.execute("SELECT 1")
