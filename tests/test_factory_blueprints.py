import importlib
import sys

import pytest

from app import create_app


class FakeNLP:
    instances = 0

    def __init__(self, **_kwargs):
        type(self).instances += 1


class FakeGenerator:
    instances = 0

    def __init__(self, nlp_engine):
        self.nlp_engine = nlp_engine
        type(self).instances += 1


@pytest.fixture
def app(tmp_path):
    FakeNLP.instances = 0
    FakeGenerator.instances = 0
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-that-is-longer-than-32-characters",
        "DATABASE": str(tmp_path / "test.db"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "NLP_ENGINE_FACTORY": FakeNLP,
        "EXTRACTIVE_CV_FACTORY": FakeGenerator,
    })


def test_import_has_no_application_or_nlp_model(monkeypatch):
    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    assert not hasattr(module, "app")
    assert "nlp_engine" not in sys.modules


def test_factory_accepts_injected_mapping_and_creates_services_once(app):
    assert app.extensions["nlp_engine"].__class__ is FakeNLP
    assert app.extensions["extractive_cv_generator"].__class__ is FakeGenerator
    assert FakeNLP.instances == FakeGenerator.instances == 1


def test_default_factory_fails_closed_without_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"NLP_ENGINE_FACTORY": FakeNLP, "EXTRACTIVE_CV_FACTORY": FakeGenerator})


def test_blueprints_and_public_routes_are_registered(app):
    assert {"health", "recruiter", "job_search"} <= set(app.blueprints)
    expected = {
        "/health": {"GET"}, "/ready": {"GET"},
        "/": {"GET"}, "/upload-cv": {"GET", "POST"},
        "/job-analysis": {"GET", "POST"}, "/match/<job_id>": {"POST"},
        "/results/<job_id>": {"GET"}, "/api/delete-cv/<cv_id>": {"DELETE"},
        "/api/delete-job/<job_id>": {"DELETE"}, "/download_cv/<cv_id>": {"GET"},
        "/api/stats": {"GET"}, "/job-search": {"GET"},
        "/api/job-search/upload-cv": {"POST"}, "/api/job-search/parse-job": {"POST"},
        "/api/job-search/generate-cv": {"POST"}, "/api/job-search/download-cv/<session_id>": {"GET"},
        "/api/job-search/delete-session/<session_id>": {"DELETE"},
        "/api/job-search/delete-profile/<profile_id>": {"DELETE"},
    }
    actual = {rule.rule: rule.methods - {"HEAD", "OPTIONS"} for rule in app.url_map.iter_rules()}
    assert expected.items() <= actual.items()


def test_health_and_readiness_endpoints(app, monkeypatch):
    monkeypatch.setattr("routes.health.find_spec", lambda _name: object())

    health = app.test_client().get("/health")
    ready = app.test_client().get("/ready")

    assert health.status_code == 200
    assert health.get_json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.get_json()["status"] == "ready"
    assert all(ready.get_json()["checks"].values())


def test_readiness_reports_missing_spacy_model(app, monkeypatch):
    monkeypatch.setattr("routes.health.find_spec", lambda _name: None)

    response = app.test_client().get("/ready")

    assert response.status_code == 503
    assert response.get_json()["checks"]["spacy_model"] is False


@pytest.mark.parametrize("url, nav_id", [
    ("/", b'id="nav-dashboard"'), ("/upload-cv", b'id="nav-upload"'),
    ("/job-analysis", b'id="nav-jobs"'), ("/job-search", b'id="nav-job-search"'),
])
def test_page_smoke_renders_with_active_navigation(app, url, nav_id):
    response = app.test_client().get(url)
    assert response.status_code == 200
    marker = response.data.index(nav_id)
    assert b"active" in response.data[marker - 120:marker + 180]


def test_factory_accepts_non_dict_mapping_config(tmp_path):
    from collections import UserDict

    app = create_app(UserDict({
        "TESTING": True,
        "SECRET_KEY": "mapping-secret-key-that-is-longer-than-32-characters",
        "DATABASE": str(tmp_path / "mapping.db"),
        "UPLOAD_FOLDER": str(tmp_path / "mapping-uploads"),
        "NLP_ENGINE_FACTORY": FakeNLP,
        "EXTRACTIVE_CV_FACTORY": FakeGenerator,
    }))

    assert app.config["TESTING"] is True


def test_factory_accepts_config_class(tmp_path):
    class TestConfig:
        TESTING = True
        SECRET_KEY = "class-secret-key-that-is-longer-than-32-characters"
        DATABASE = str(tmp_path / "class.db")
        UPLOAD_FOLDER = str(tmp_path / "class-uploads")
        NLP_ENGINE_FACTORY = FakeNLP
        EXTRACTIVE_CV_FACTORY = FakeGenerator

    app = create_app(TestConfig)

    assert app.config["TESTING"] is True


def test_clean_text_uses_single_source_and_preserves_output():
    from nlp_engine import clean_text as engine_clean_text
    from routes.recruiter import clean_text as recruiter_clean_text
    from text_utils import clean_text

    source = " RT Hello! https://example.com #tag @name cc C++ / Python\n"
    assert clean_text(source) == "hello c++ / python"
    assert clean_text(None) == ""
    assert engine_clean_text is clean_text
    assert recruiter_clean_text is clean_text
