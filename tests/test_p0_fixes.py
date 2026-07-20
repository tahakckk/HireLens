from io import BytesIO
import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from file_validation import validate_cv_file


def load_app(monkeypatch, tmp_path):
    """Build a test application with injected, lightweight services."""
    import app as application

    class FakeNLPEngine:
        def __init__(self, **_kwargs):
            pass

    class FakeGenerator:
        def __init__(self, **_kwargs):
            pass

    flask_app = application.create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-that-is-longer-than-32-characters",
        "DATABASE": str(tmp_path / "test.db"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "NLP_ENGINE_FACTORY": FakeNLPEngine,
        "EXTRACTIVE_CV_FACTORY": FakeGenerator,
    })
    return application, flask_app

def test_application_startup_rejects_blank_example_secret(monkeypatch):
    example_secret = next(
        line.split('=', 1)[1]
        for line in (PROJECT_ROOT / '.env.example').read_text().splitlines()
        if line.startswith('SECRET_KEY=')
    )
    monkeypatch.setenv('SECRET_KEY', example_secret)
    import app as application

    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        application.create_app({'NLP_ENGINE_FACTORY': lambda **kwargs: None, 'EXTRACTIVE_CV_FACTORY': lambda **kwargs: None})


def test_application_startup_accepts_real_secret(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)

    assert flask_app.config['SECRET_KEY'] == 'test-secret-key-that-is-longer-than-32-characters'


def test_allowed_file_accepts_only_pdf_and_docx(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)

    from routes.helpers import allowed_file
    with flask_app.app_context():
        assert allowed_file('resume.PDF')
        assert allowed_file('resume.docx')
        assert not allowed_file('resume.doc')
        assert not allowed_file('resume.pdf.exe')


def test_cv_content_validation_rejects_fake_files_and_accepts_minimal_files(tmp_path):
    fake_pdf = tmp_path / 'fake.pdf'
    fake_pdf.write_text('not a PDF')
    fake_docx = tmp_path / 'fake.docx'
    fake_docx.write_text('not a DOCX')
    valid_pdf = tmp_path / 'valid.pdf'
    valid_pdf.write_bytes(b'%PDF-1.4\nminimal')
    valid_docx = tmp_path / 'valid.docx'
    with zipfile.ZipFile(valid_docx, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('word/document.xml', '<w:document/>')

    assert not validate_cv_file(str(fake_pdf))
    assert not validate_cv_file(str(fake_docx))
    assert validate_cv_file(str(valid_pdf))
    assert validate_cv_file(str(valid_docx))


def test_upload_endpoints_reject_invalid_content_and_clean_up(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)
    client = flask_app.test_client()

    main_response = client.post(
        '/upload-cv',
        data={'files': (BytesIO(b'not a PDF'), 'resume.pdf')},
        content_type='multipart/form-data',
    )
    search_response = client.post(
        '/api/job-search/upload-cv',
        data={'file': (BytesIO(b'not a DOCX'), 'resume.docx')},
        content_type='multipart/form-data',
    )

    assert main_response.status_code == 302
    assert search_response.status_code == 400
    assert search_response.get_json()['error'] == 'Dosya içeriği geçersiz veya desteklenmiyor.'
    assert list((tmp_path / 'uploads').iterdir()) == []


def test_file_preview_uses_text_content_for_file_names():
    source = (PROJECT_ROOT / 'static/js/app.js').read_text()

    assert 'name.textContent = `${isSupported ? \'📄\' : \'⚠️\'} ${file.name}`;' in source
    assert '${file.name}</span>' not in source


def test_delete_cv_removes_safe_upload_and_related_matches(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)
    uploaded_file = tmp_path / 'uploads' / 'stored_resume.pdf'
    uploaded_file.write_text('cv')

    with flask_app.app_context():
        db = __import__('database', fromlist=['get_db']).get_db()
        db.execute("INSERT INTO cvs (id, filename, file_path) VALUES (?, ?, ?)", ('cv-1', 'resume.pdf', uploaded_file.name))
        db.execute("INSERT INTO jobs (id, title, description) VALUES (?, ?, ?)", ('job-1', 'Role', 'Description'))
        db.execute("INSERT INTO matches (id, job_id, cv_id) VALUES (?, ?, ?)", ('match-1', 'job-1', 'cv-1'))
        db.commit()

    response = flask_app.test_client().delete('/api/delete-cv/cv-1')

    assert response.status_code == 200
    assert not uploaded_file.exists()
    with flask_app.app_context():
        db = __import__('database', fromlist=['get_db']).get_db()
        assert db.execute("SELECT 1 FROM cvs WHERE id = 'cv-1'").fetchone() is None
        assert db.execute("SELECT 1 FROM matches WHERE id = 'match-1'").fetchone() is None


def test_delete_cv_does_not_follow_traversal_path(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)
    outside_file = tmp_path / 'outside.pdf'
    outside_file.write_text('must remain')

    with flask_app.app_context():
        db = __import__('database', fromlist=['get_db']).get_db()
        db.execute("INSERT INTO cvs (id, filename, file_path) VALUES (?, ?, ?)", ('cv-2', 'resume.pdf', '../outside.pdf'))
        db.commit()

    response = flask_app.test_client().delete('/api/delete-cv/cv-2')

    assert response.status_code == 200
    assert outside_file.exists()


def test_delete_cv_preserves_file_when_database_commit_fails(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)
    uploaded_file = tmp_path / 'uploads' / 'stored_resume.pdf'
    uploaded_file.write_text('cv')

    with flask_app.app_context():
        db = __import__('database', fromlist=['get_db']).get_db()
        db.execute("INSERT INTO cvs (id, filename, file_path) VALUES (?, ?, ?)", ('cv-3', 'resume.pdf', uploaded_file.name))
        db.commit()

    class FailingCommitDB:
        def __init__(self, database):
            self.database = database

        def execute(self, *args):
            return self.database.execute(*args)

        def commit(self):
            raise sqlite3.OperationalError('forced commit failure')

        def rollback(self):
            self.database.rollback()

    with flask_app.app_context():
        failing_db = FailingCommitDB(__import__('database', fromlist=['get_db']).get_db())
        original_get_db = __import__('database', fromlist=['get_db']).get_db
        monkeypatch.setattr('routes.recruiter.get_db', lambda: failing_db)
        response = flask_app.test_client().delete('/api/delete-cv/cv-3')
        monkeypatch.setattr('routes.recruiter.get_db', original_get_db)

    assert response.status_code == 500
    assert uploaded_file.exists()
    with flask_app.app_context():
        db = __import__('database', fromlist=['get_db']).get_db()
        assert db.execute("SELECT 1 FROM cvs WHERE id = 'cv-3'").fetchone() is not None


def test_delete_cv_reports_staged_file_cleanup_failure(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)
    uploaded_file = tmp_path / 'uploads' / 'stored_resume.pdf'
    uploaded_file.write_text('cv')
    with flask_app.app_context():
        db = __import__('database', fromlist=['get_db']).get_db()
        db.execute("INSERT INTO cvs (id, filename, file_path) VALUES (?, ?, ?)", ('cv-4', 'resume.pdf', uploaded_file.name))
        db.commit()

    original_unlink = Path.unlink

    def fail_staged_unlink(path, *args, **kwargs):
        if path.name.startswith('.deleting-'):
            raise OSError('forced cleanup failure')
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', fail_staged_unlink)
    response = flask_app.test_client().delete('/api/delete-cv/cv-4')

    assert response.status_code == 200
    assert response.get_json()['cleanup_pending'] is True
    assert not uploaded_file.exists()


def test_job_analysis_hides_internal_exception_details(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)

    response = flask_app.test_client().post(
        '/job-analysis',
        data={'title': 'Engineer', 'description': 'A sufficiently detailed job description'},
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'İş ilanı analiz edilemedi. Lütfen tekrar deneyin.' in body
    assert 'has no attribute' not in body


def test_tailored_cv_endpoint_hides_internal_exception_details(monkeypatch, tmp_path):
    application, flask_app = load_app(monkeypatch, tmp_path)
    with flask_app.app_context():
        db = __import__('database', fromlist=['get_db']).get_db()
        db.execute(
            """INSERT INTO user_profiles
               (id, original_filename, original_text, profile_data, extracted_skills, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ('profile-1', 'resume.pdf', 'resume', '{}', '[]', '2026-07-20T00:00:00'),
        )
        db.commit()

    response = flask_app.test_client().post(
        '/api/job-search/generate-cv',
        json={'profile_id': 'profile-1', 'job_data': {'title': 'Engineer'}},
    )

    payload = response.get_json()
    assert response.status_code == 500
    assert payload['error'] == 'CV oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.'
    assert 'has no attribute' not in payload['error']
