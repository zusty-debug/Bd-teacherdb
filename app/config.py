"""Application configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_db_url(url: str) -> str:
    """Render/Heroku provide 'postgres://...' but SQLAlchemy wants
    'postgresql://...'. Also switch to the psycopg2 driver explicitly."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


# Default to a local SQLite file for quick dev; set DATABASE_URL for Postgres.
DATABASE_URL = _normalize_db_url(
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://studentapi:studentapi@localhost:5432/student_api_test",
    )
)

# Master key for admin operations (create/revoke API keys).
# MUST be set in production. A dev fallback is provided so the app can boot locally.
MASTER_KEY = os.getenv("MASTER_KEY", "dev-master-key-change-me")

# Hard cap on page size to prevent abuse.
MAX_PER_PAGE = int(os.getenv("MAX_PER_PAGE", "500"))
