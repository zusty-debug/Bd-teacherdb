"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (register models with Base)
from .config import MASTER_KEY
from .database import Base, engine, setup_postgres_indexes
from .routers import admin, health, schools, students


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on boot (idempotent). Fine for v1; swap for Alembic migrations
    # later if schema changes become frequent.
    Base.metadata.create_all(bind=engine)
    setup_postgres_indexes()
    if MASTER_KEY == "dev-master-key-change-me":
        import logging

        logging.getLogger("uvicorn.error").warning(
            "WARNING: MASTER_KEY is using the insecure dev default. "
            "Set the MASTER_KEY environment variable before deploying."
        )
    yield


app = FastAPI(
    title="Student Records API",
    description=(
        "Centralized multi-school student records API.\n\n"
        "**Data endpoints** require an `X-API-Key` header.\n"
        "**Admin endpoints** (/admin) require an `X-Master-Key` header.\n\n"
        "Generate an API key first: `POST /api/v1/admin/keys` with the master key."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the UI (and any client) to call the API from the browser during development.
# Tighten `allow_origins` to the real UI domain in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(students.router)
app.include_router(schools.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "Student Records API",
        "docs": "/docs",
        "health": "/health",
    }
