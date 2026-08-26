"""Authentication: master key + API keys.

Two tiers:
  * Master key  -> one secret held by the admin (env var MASTER_KEY).
                   Used only on /admin endpoints to create/revoke API keys.
  * API keys    -> random tokens stored as SHA-256 hashes. Clients send one
                   in the `X-API-Key` header for all data endpoints.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from . import models
from .config import MASTER_KEY
from .database import get_db

KEY_PREFIX = "sk_"


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Return (full_key, display_prefix)."""
    token = KEY_PREFIX + secrets.token_hex(32)
    prefix = token[:14]
    return token, prefix


def verify_master_key(x_master_key: str | None = Header(default=None)) -> None:
    if not MASTER_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MASTER_KEY is not configured on the server.",
        )
    if not x_master_key or not hmac.compare_digest(x_master_key, MASTER_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing master key.",
        )


def require_api_key(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.ApiKey:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Pass it in the X-API-Key header.",
        )
    key = (
        db.query(models.ApiKey)
        .filter(models.ApiKey.key_hash == hash_key(x_api_key))
        .first()
    )
    if not key or not key.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
        )
    # Best-effort last-used tracking (non-fatal on failure).
    try:
        key.last_used_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
    return key
