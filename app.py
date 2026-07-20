"""HireLens application factory and development entry point."""
import os

from flask import Flask

from config import Config
from database import init_app, init_db


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object is None:
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    if config_object:
        if isinstance(config_object, type):
            app.config.from_object(config_object)
        else:
            app.config.update(config_object)
    Config.validate(app.config.get("SECRET_KEY"))
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_app(app)

    engine_factory = app.config.get("NLP_ENGINE_FACTORY")
    if engine_factory is None:
        from nlp_engine import NLPEngine
        engine_factory = NLPEngine
    engine = engine_factory(
        sbert_model_name=app.config["SBERT_MODEL"], spacy_model_name=app.config["SPACY_MODEL"]
    )
    generator_factory = app.config.get("EXTRACTIVE_CV_FACTORY")
    if generator_factory is None:
        from extractive_cv import ExtractiveCVGenerator
        generator_factory = ExtractiveCVGenerator
    app.extensions["nlp_engine"] = engine
    app.extensions["extractive_cv_gen"] = generator_factory(nlp_engine=engine)

    from routes import job_search_bp, recruiter_bp
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(job_search_bp)
    with app.app_context():
        init_db()
    return app


if __name__ == "__main__":
    create_app().run(debug=False, port=5000)
