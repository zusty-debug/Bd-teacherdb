"""Application configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Default to a local SQLite file for quick dev; set DATABASE_URL for Postgres.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://studentapi:studentapi@localhost:5432/student_api_test"
)

# Master key for admin operations (create/revoke API keys).
# MUST be set in production. A dev fallback is provided so the app can boot locally.
MASTER_KEY = os.getenv("MASTER_KEY", "dev-master-key-change-me")

# Hard cap on page size to prevent abuse.
MAX_PER_PAGE = int(os.getenv("MAX_PER_PAGE", "500"))
