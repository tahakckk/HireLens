import os
import sqlite3

os.environ.setdefault('SECRET_KEY', 'architecture-test-secret-key-that-is-longer-than-32-characters')

from app import create_app


class FakeEngine:
    def __init__(self, **_kwargs):
        pass


class FakeGenerator:
    def __init__(self, **_kwargs):
        pass


def make_app(tmp_path):
    return create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-that-is-longer-than-32-characters',
        'DATABASE': str(tmp_path / 'hirelens.db'),
        'UPLOAD_FOLDER': str(tmp_path / 'uploads'),
        'NLP_ENGINE_FACTORY': FakeEngine,
        'EXTRACTIVE_CV_FACTORY': FakeGenerator,
    })


def test_factory_registers_main_blueprint_and_keeps_public_urls(tmp_path):
    application = make_app(tmp_path)
    assert {'recruiter', 'job_search'} <= set(application.blueprints)
    rules = {rule.rule for rule in application.url_map.iter_rules()}
    assert {'/', '/upload-cv', '/api/delete-cv/<cv_id>', '/api/job-search/upload-cv'} <= rules


def test_database_initialization_is_idempotent_and_enforces_foreign_keys(tmp_path):
    application = make_app(tmp_path)
    with application.app_context():
        from database import get_db, init_db
        init_db()
        db = get_db()
        assert db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        assert db.execute('PRAGMA journal_mode').fetchone()[0].lower() == 'wal'
        with __import__('pytest').raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO matches (id, job_id, cv_id) VALUES ('bad', 'missing-job', 'missing-cv')")


def test_factory_initializes_models_through_injected_factory(tmp_path):
    calls = []

    class RecordingEngine(FakeEngine):
        def __init__(self, **kwargs):
            calls.append(kwargs)

    application = create_app({
        'TESTING': True, 'SECRET_KEY': 'test-secret-key-that-is-longer-than-32-characters',
        'DATABASE': str(tmp_path / 'models.db'), 'UPLOAD_FOLDER': str(tmp_path / 'uploads'),
        'NLP_ENGINE_FACTORY': RecordingEngine, 'EXTRACTIVE_CV_FACTORY': FakeGenerator,
    })
    assert len(calls) == 1
    assert application.extensions['nlp_engine'].__class__ is RecordingEngine


def test_public_pages_render_and_mark_active_navigation(tmp_path):
    application = make_app(tmp_path)
    client = application.test_client()
    expected = {
        '/': 'id="nav-dashboard"',
        '/upload-cv': 'id="nav-upload"',
        '/job-analysis': 'id="nav-jobs"',
        '/job-search': 'id="nav-job-search"',
    }
    for url, marker in expected.items():
        response = client.get(url)
        assert response.status_code == 200
        page = response.get_data(as_text=True)
        assert marker in page
        active_link = page[page.index(marker) - 120:page.index(marker)]
        assert 'active' in active_link
