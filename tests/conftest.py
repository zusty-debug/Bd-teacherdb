import os

# Configure the app BEFORE importing it so config.py picks up these values.
os.environ.setdefault("MASTER_KEY", "test-master-key")
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db"),
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402  (register models)
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

MASTER_KEY = "test-master-key"


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def master_headers():
    return {"X-Master-Key": MASTER_KEY}


@pytest.fixture()
def api_key(client, master_headers):
    """Create an API key and return its headers."""
    resp = client.post("/api/v1/admin/keys", json={"name": "test"}, headers=master_headers)
    assert resp.status_code == 201, resp.text
    key = resp.json()["key"]
    return {"X-API-Key": key}
