import os
from dotenv import load_dotenv

load_dotenv()


def _database_uri():
    """Get DATABASE_URL and normalize for SQLAlchemy (e.g. Render uses postgres://)."""
    uri = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/wvc"
    )
    # Render and some hosts set postgres://; SQLAlchemy requires postgresql://
    if uri and uri.startswith("postgres://"):
        uri = "postgresql://" + uri[len("postgres://"):]
    return uri


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # For Alembic migrations inside Flask-Migrate
    # Avoids deprecated MetaData warnings
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }
