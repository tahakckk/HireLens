import json
from pathlib import Path

import pytest

from app import create_app
from repositories import JobSearchRepository, RecruiterRepository


class FakeNLP:
    def __init__(self, **_kwargs):
        pass


class FakeGenerator:
    def __init__(self, **_kwargs):
        pass


@pytest.fixture
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "repository-test-secret-longer-than-32-characters",
        "DATABASE": str(tmp_path / "repository.db"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "NLP_ENGINE_FACTORY": FakeNLP,
        "EXTRACTIVE_CV_FACTORY": FakeGenerator,
    })


def test_recruiter_repository_creates_and_lists_cv_and_job(app):
    with app.app_context():
        repository = RecruiterRepository()
        repository.create_cv({
            "id": "cv-1", "filename": "resume.pdf", "file_path": "resume.pdf",
            "original_text": "Python developer", "cleaned_text": "python developer",
            "extracted_skills": '["python"]', "timeline": "[]",
            "experience_months": 12, "skill_recency": "{}", "metadata": "{}",
            "embedding": b"embedding", "uploaded_at": "2026-07-20T00:00:00",
        })
        repository.create_job({
            "id": "job-1", "title": "Engineer", "description": "Python role",
            "cleaned_description": "python role", "required_skills": '["python"]',
            "must_have_skills": '["python"]', "nice_to_have_skills": "[]",
            "embedding": b"embedding", "created_at": "2026-07-20T00:00:00",
        })

        assert repository.stats() == {"cv_count": 1, "job_count": 1, "match_count": 0}
        assert repository.find_job("job-1")["title"] == "Engineer"
        assert repository.find_cv_file("cv-1")["filename"] == "resume.pdf"


def test_job_search_repository_preserves_profile_session_relationship(app):
    with app.app_context():
        repository = JobSearchRepository()
        repository.create_profile({
            "id": "profile-1", "original_filename": "resume.pdf",
            "original_text": "Profile", "profile_data": json.dumps({"name": "Taha"}),
            "extracted_skills": '["python"]', "created_at": "2026-07-20T00:00:00",
        })
        repository.create_session({
            "id": "session-1", "profile_id": "profile-1", "job_url": "",
            "job_data": json.dumps({"title": "Engineer"}),
            "optimized_cv": json.dumps({"full_name": "Taha"}),
            "status": "completed", "created_at": "2026-07-20T00:00:00",
        })

        assert repository.find_profile("profile-1") is not None
        assert repository.find_session("session-1")["status"] == "completed"
        assert repository.list_recent_sessions()[0]["original_filename"] == "resume.pdf"

        repository.delete_profile("profile-1")
        assert repository.find_profile("profile-1") is None
        assert repository.find_session("session-1") is None


def test_delete_endpoints_use_named_repository_operations(app):
    with app.app_context():
        repository = RecruiterRepository()
        repository.create_job({
            "id": "job-delete", "title": "Delete me", "description": "Description",
            "cleaned_description": "description", "required_skills": "[]",
            "must_have_skills": "[]", "nice_to_have_skills": "[]",
            "embedding": b"", "created_at": "2026-07-20T00:00:00",
        })

    response = app.test_client().delete("/api/delete-job/job-delete")

    assert response.status_code == 200
    with app.app_context():
        assert RecruiterRepository().find_job("job-delete") is None


def test_route_modules_contain_no_database_queries():
    for path in (Path("routes/recruiter.py"), Path("routes/job_search.py")):
        source = path.read_text()
        assert ".execute(" not in source
        assert "SELECT " not in source
        assert "INSERT " not in source
        assert "DELETE FROM" not in source
        assert ".commit(" not in source
        assert ".rollback(" not in source
