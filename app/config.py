import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/wvc"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # For Alembic migrations inside Flask-Migrate
    # Avoids deprecated MetaData warnings
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }
