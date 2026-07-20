"""HireLens Flask application factory."""
import os

from flask import Flask

from config import Config
from database import init_app as init_database_app
from database import init_db


def _validate_secret_key(app):
    secret_key = app.config.get("SECRET_KEY")
    if not secret_key or len(secret_key) < 32:
        raise RuntimeError(
            "SECRET_KEY ortam değişkeni en az 32 karakterlik güvenli bir değer olmalıdır."
        )


def _create_services(app):
    nlp_factory = app.config.get("NLP_ENGINE_FACTORY")
    cv_factory = app.config.get("EXTRACTIVE_CV_FACTORY")

    if nlp_factory is None:
        from nlp_engine import NLPEngine
        nlp_factory = NLPEngine
    nlp_engine = nlp_factory(
        sbert_model_name=app.config["SBERT_MODEL"],
        spacy_model_name=app.config["SPACY_MODEL"],
    )

    if cv_factory is None:
        from extractive_cv import ExtractiveCVGenerator
        cv_factory = ExtractiveCVGenerator
    app.extensions["nlp_engine"] = nlp_engine
    app.extensions["extractive_cv_generator"] = cv_factory(nlp_engine=nlp_engine)


def create_app(config_object=None):
    """Build a configured application without import-time side effects."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    if config_object is not None:
        if isinstance(config_object, dict):
            app.config.from_mapping(config_object)
        else:
            app.config.from_object(config_object)
    _validate_secret_key(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_database_app(app)
    with app.app_context():
        init_db()
    _create_services(app)

    from routes import job_search_bp, recruiter_bp
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(job_search_bp)
    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=False)
