from io import BytesIO
import sqlite3
import zipfile

import pytest

from app import create_app
from config import Config
from database import get_db
from file_validation import validate_cv_file


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
        'DATABASE': str(tmp_path / 'test.db'),
        'UPLOAD_FOLDER': str(tmp_path / 'uploads'),
        'NLP_ENGINE_FACTORY': FakeEngine,
        'EXTRACTIVE_CV_FACTORY': FakeGenerator,
    })


def test_default_factory_rejects_missing_secret(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setattr(Config, 'SECRET_KEY', None)
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        create_app()


def test_factory_accepts_config_secret_without_environment(monkeypatch, tmp_path):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    assert make_app(tmp_path).config['SECRET_KEY'].startswith('test-secret')


def test_cv_content_validation_rejects_fake_files_and_accepts_minimal_files(tmp_path):
    fake_pdf = tmp_path / 'fake.pdf'; fake_pdf.write_text('not a PDF')
    fake_docx = tmp_path / 'fake.docx'; fake_docx.write_text('not a DOCX')
    valid_pdf = tmp_path / 'valid.pdf'; valid_pdf.write_bytes(b'%PDF-1.4\nminimal')
    valid_docx = tmp_path / 'valid.docx'
    with zipfile.ZipFile(valid_docx, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('word/document.xml', '<w:document/>')
    assert not validate_cv_file(str(fake_pdf))
    assert not validate_cv_file(str(fake_docx))
    assert validate_cv_file(str(valid_pdf))
    assert validate_cv_file(str(valid_docx))


def test_upload_rejects_invalid_content_and_cleans_file(tmp_path):
    app = make_app(tmp_path)
    response = app.test_client().post('/upload-cv', data={'files': (BytesIO(b'not PDF'), 'resume.pdf')}, content_type='multipart/form-data')
    assert response.status_code == 302
    assert list((tmp_path / 'uploads').iterdir()) == []


def test_delete_cv_removes_related_matches_and_safe_file(tmp_path):
    app = make_app(tmp_path)
    uploaded = tmp_path / 'uploads' / 'stored.pdf'; uploaded.write_text('cv')
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO cvs (id, filename, file_path) VALUES ('cv', 'resume.pdf', 'stored.pdf')")
        db.execute("INSERT INTO jobs (id, title, description) VALUES ('job', 'Role', 'Description')")
        db.execute("INSERT INTO matches (id, job_id, cv_id) VALUES ('match', 'job', 'cv')")
        db.commit()
    assert app.test_client().delete('/api/delete-cv/cv').status_code == 200
    assert not uploaded.exists()
    with app.app_context():
        assert get_db().execute("SELECT 1 FROM matches WHERE id = 'match'").fetchone() is None


def test_foreign_key_enforcement_rejects_orphan_match(tmp_path):
    app = make_app(tmp_path)
    with app.app_context(), pytest.raises(sqlite3.IntegrityError):
        get_db().execute("INSERT INTO matches (id, job_id, cv_id) VALUES ('bad', 'none', 'none')")
