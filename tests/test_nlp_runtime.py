from pathlib import Path

import pytest


def test_spacy_model_is_an_application_dependency():
    requirements = Path("requirements.txt").read_text()

    assert "en-core-web-sm" in requirements


def test_missing_spacy_model_fails_without_runtime_download(monkeypatch):
    import nlp_engine

    monkeypatch.setattr(
        nlp_engine.spacy,
        "load",
        lambda _name: (_ for _ in ()).throw(OSError("model is not installed")),
    )
    engine = nlp_engine.NLPEngine(spacy_model_name="missing_test_model")

    with pytest.raises(RuntimeError, match="Required spaCy model"):
        engine.extract_skills("Python Flask Docker")

    source = Path("nlp_engine.py").read_text()
    assert "subprocess.run" not in source
    assert "spacy download" not in source
