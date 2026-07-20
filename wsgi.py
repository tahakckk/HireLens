"""Production WSGI entry point (for example: gunicorn wsgi:app)."""
from app import create_app
app = create_app()
