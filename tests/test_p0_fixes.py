import importlib
import sys
import types
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def load_app(monkeypatch, tmp_path):
    """Import the Flask app without loading the heavyweight NLP models."""
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-that-is-longer-than-32-characters')

    nlp_module = types.ModuleType('nlp_engine')

    class FakeNLPEngine:
        def __init__(self, **_kwargs):
            pass

    nlp_module.NLPEngine = FakeNLPEngine
    nlp_module.clean_text = lambda text: text
    monkeypatch.setitem(sys.modules, 'nlp_engine', nlp_module)

    scraper_module = types.ModuleType('job_scraper')
    scraper_module.scrape_linkedin_job = lambda _url: None
    scraper_module.parse_job_text = lambda *_args: None
    scraper_module.validate_linkedin_url = lambda _url: False
    monkeypatch.setitem(sys.modules, 'job_scraper', scraper_module)

    cv_module = types.ModuleType('extractive_cv')

    class FakeGenerator:
        def __init__(self, **_kwargs):
            pass

    cv_module.ExtractiveCVGenerator = FakeGenerator
    monkeypatch.setitem(sys.modules, 'extractive_cv', cv_module)

    sys.modules.pop('config', None)
    sys.modules.pop('app', None)
    application = importlib.import_module('app')
    application.app.config.update(
        TESTING=True,
        DATABASE=str(tmp_path / 'test.db'),
        UPLOAD_FOLDER=str(tmp_path / 'uploads'),
    )
    application.os.makedirs(application.app.config['UPLOAD_FOLDER'], exist_ok=True)
    application.init_db()
    return application


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    sys.modules.pop('config', None)
    config = importlib.import_module('config')

    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        config.Config.validate()


def test_allowed_file_accepts_only_pdf_and_docx(monkeypatch, tmp_path):
    application = load_app(monkeypatch, tmp_path)

    assert application.allowed_file('resume.PDF')
    assert application.allowed_file('resume.docx')
    assert not application.allowed_file('resume.doc')
    assert not application.allowed_file('resume.pdf.exe')


def test_delete_cv_removes_safe_upload_and_related_matches(monkeypatch, tmp_path):
    application = load_app(monkeypatch, tmp_path)
    uploaded_file = tmp_path / 'uploads' / 'stored_resume.pdf'
    uploaded_file.write_text('cv')

    with application.app.app_context():
        db = application.get_db()
        db.execute("INSERT INTO cvs (id, filename, file_path) VALUES (?, ?, ?)", ('cv-1', 'resume.pdf', uploaded_file.name))
        db.execute("INSERT INTO jobs (id, title, description) VALUES (?, ?, ?)", ('job-1', 'Role', 'Description'))
        db.execute("INSERT INTO matches (id, job_id, cv_id) VALUES (?, ?, ?)", ('match-1', 'job-1', 'cv-1'))
        db.commit()

    response = application.app.test_client().delete('/api/delete-cv/cv-1')

    assert response.status_code == 200
    assert not uploaded_file.exists()
    with application.app.app_context():
        db = application.get_db()
        assert db.execute("SELECT 1 FROM cvs WHERE id = 'cv-1'").fetchone() is None
        assert db.execute("SELECT 1 FROM matches WHERE id = 'match-1'").fetchone() is None


def test_delete_cv_does_not_follow_traversal_path(monkeypatch, tmp_path):
    application = load_app(monkeypatch, tmp_path)
    outside_file = tmp_path / 'outside.pdf'
    outside_file.write_text('must remain')

    with application.app.app_context():
        db = application.get_db()
        db.execute("INSERT INTO cvs (id, filename, file_path) VALUES (?, ?, ?)", ('cv-2', 'resume.pdf', '../outside.pdf'))
        db.commit()

    response = application.app.test_client().delete('/api/delete-cv/cv-2')

    assert response.status_code == 200
    assert outside_file.exists()
