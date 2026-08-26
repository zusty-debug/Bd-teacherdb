"""Database engine, session factory, and base declarative class."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import DATABASE_URL

# SQLite needs special handling for cross-thread access (FastAPI runs sync
# endpoints in a threadpool). Postgres uses a normal pooled engine.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_postgres_indexes() -> None:
    """Create pg_trgm indexes for fast ILIKE '%term%' search (Postgres only).

    Skipped silently on SQLite (which uses a simple table scan for dev).
    """
    if not DATABASE_URL.startswith("postgresql"):
        return
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        for col in ("name", "name_bn", "mobile_no", "email", "nid", "father_name"):
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS ix_employees_{col}_trgm "
                    f"ON employees USING gin (lower({col}) gin_trgm_ops)"
                )
            )
