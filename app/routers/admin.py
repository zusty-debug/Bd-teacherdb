"""Admin endpoints for managing API keys (require the master key).

All routes here are protected by the `X-Master-Key` header.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import generate_api_key, hash_key, verify_master_key

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(verify_master_key)],
)


@router.post("/keys", response_model=schemas.ApiKeyCreated, status_code=201)
def create_key(payload: schemas.ApiKeyCreate, db: Session = Depends(get_db)):
    if payload.institution_id is not None:
        inst = db.query(models.Institution).filter(models.Institution.id == payload.institution_id).first()
        if not inst:
            raise HTTPException(status_code=400, detail="institution_id does not exist")

    full_key, prefix = generate_api_key()
    key = models.ApiKey(
        name=payload.name,
        key_hash=hash_key(full_key),
        key_prefix=prefix,
        institution_id=payload.institution_id,
        active=True,
    )
    db.add(key)
    db.commit()
    db.refresh(key)

    out = schemas.ApiKeyCreated.model_validate(key)
    out.key = full_key
    return out


@router.get("/keys", response_model=list[schemas.ApiKeyOut])
def list_keys(db: Session = Depends(get_db)):
    return db.query(models.ApiKey).order_by(models.ApiKey.created_at.desc()).all()


@router.delete("/keys/{key_id}", status_code=204)
def revoke_key(key_id: int, db: Session = Depends(get_db)):
    key = db.query(models.ApiKey).filter(models.ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.active = False
    db.commit()


@router.post("/keys/{key_id}/toggle", response_model=schemas.ApiKeyOut)
def toggle_key(key_id: int, db: Session = Depends(get_db)):
    key = db.query(models.ApiKey).filter(models.ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.active = not key.active
    db.commit()
    db.refresh(key)
    return key
