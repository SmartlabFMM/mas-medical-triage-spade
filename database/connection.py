from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import os
from dotenv import load_dotenv, find_dotenv
import logging

logger = logging.getLogger(__name__)

# Find project root .env by searching parent directories
_env_path = find_dotenv(filename='.env', raise_error_if_not_found=False)
if _env_path:
    load_dotenv(dotenv_path=_env_path, override=True)
    print(f"[DB] .env loaded from {_env_path}")
else:
    print("[DB] No .env file found in parent directories")

db = SQLAlchemy()


def init_app(app: Flask):
    """
    Initialize the Flask‑SQLAlchemy extension with the given app.
    Call this once at application startup.
    """
    # Get DATABASE_URL from environment (loaded from .env)
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        database_url = 'postgresql://postgres:postgres@localhost:5432/mas_triage_db'
        print(f"[WARNING] DATABASE_URL not set, using default: {database_url}")

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 20,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'connect_args': {'connect_timeout': 10, 'client_encoding': 'utf-8'}
    }
    db.init_app(app)

    # Attempt to create tables; ignore failures to allow startup.
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables ensured.")
        except Exception as e:
            logger.warning(f"Table creation skipped (non‑fatal): {e}")

    return db


def get_db():
    """
    Return the SQLAlchemy instance (for use in repositories or scripts).
    """
    return db
