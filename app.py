"""HireLens application factory and development entry point."""
import os
import sqlite3  # noqa: F401
from flask import Flask
from werkzeug.local import LocalProxy
from config import Config
from database import get_db, init_app, init_db as _init_db  # noqa: F401


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object:
        app.config.from_object(config_object) if isinstance(config_object, type) else app.config.update(config_object)
    Config.validate(app.config.get('SECRET_KEY'))
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_app(app)
    from nlp_engine import NLPEngine
    from extractive_cv import ExtractiveCVGenerator
    engine_factory = app.config.get('NLP_ENGINE_FACTORY', NLPEngine)
    engine = engine_factory(sbert_model_name=app.config['SBERT_MODEL'], spacy_model_name=app.config['SPACY_MODEL'])
    app.extensions['nlp_engine'] = engine
    app.extensions['extractive_cv_gen'] = app.config.get('EXTRACTIVE_CV_FACTORY', ExtractiveCVGenerator)(nlp_engine=engine)
    from routes import job_search_bp, recruiter_bp
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(job_search_bp)
    with app.app_context():
        _init_db()
    return app


# Validate security configuration at import time without loading NLP models.
Config.validate()
_application = None
def _get_application():
    global _application
    if _application is None:
        _application = create_app()
    return _application
# Compatibility proxy; accessing it builds the application on demand.
app = LocalProxy(_get_application)

def init_db():
    """Compatibility helper that initializes the lazily-created application database."""
    with _get_application().app_context():
        _init_db()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in _get_application().config["ALLOWED_EXTENSIONS"]

if __name__ == '__main__':
    application = create_app()
    application.run(debug=False, port=5000)
