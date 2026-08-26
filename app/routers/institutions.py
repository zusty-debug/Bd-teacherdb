"""Institutions + aggregates + metadata (require a valid API key)."""
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import MAX_PER_PAGE
from ..database import get_db
from ..security import require_api_key

router = APIRouter(prefix="/api/v1", tags=["institutions"], dependencies=[Depends(require_api_key)])


@router.get("/institutions", response_model=list[schemas.InstitutionOut])
def list_institutions(
    search: Optional[str] = Query(default=None, description="Match EIIN or MPO code"),
    db: Session = Depends(get_db),
):
    q = (
        db.query(models.Institution, func.count(models.Employee.id).label("employee_count"))
        .outerjoin(models.Employee)
        .group_by(models.Institution.id)
        .order_by(models.Institution.eiin)
    )
    if search:
        like = f"%{search}%"
        q = q.having(
            func.lower(models.Institution.eiin).like(like)
            | func.lower(models.Institution.ins_mpo_code).like(like)
        )
    rows = q.all()
    return [
        schemas.InstitutionOut(
            id=i.id, eiin=i.eiin, ins_mpo_code=i.ins_mpo_code,
            ins_branch_id=i.ins_branch_id, ps_id=i.ps_id,
            employee_count=employee_count,
        )
        for i, employee_count in rows
    ]


@router.get("/institutions/{eiin}", response_model=schemas.InstitutionOut)
def get_institution(eiin: str, db: Session = Depends(get_db)):
    inst = db.query(models.Institution).filter(models.Institution.eiin == eiin).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    employee_count = (
        db.query(func.count(models.Employee.id))
        .filter(models.Employee.institution_id == inst.id)
        .scalar()
        or 0
    )
    return schemas.InstitutionOut(
        id=inst.id, eiin=inst.eiin, ins_mpo_code=inst.ins_mpo_code,
        ins_branch_id=inst.ins_branch_id, ps_id=inst.ps_id,
        employee_count=employee_count,
    )


@router.get("/institutions/{eiin}/employees", response_model=schemas.PaginatedEmployees)
def list_institution_employees(
    eiin: str,
    designation_name: Optional[str] = Query(default=None),
    status_name: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=MAX_PER_PAGE),
    db: Session = Depends(get_db),
):
    inst = db.query(models.Institution).filter(models.Institution.eiin == eiin).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    q = db.query(models.Employee).filter(models.Employee.institution_id == inst.id)
    if designation_name:
        q = q.filter(models.Employee.designation_name == designation_name)
    if status_name:
        q = q.filter(models.Employee.status_name == status_name)

    total = q.count()
    items = q.order_by(models.Employee.id).offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, math.ceil(total / per_page)) if total else 1

    return schemas.PaginatedEmployees(
        total=total, page=page, per_page=per_page, pages=pages,
        items=[schemas.EmployeeOut.model_validate(e) for e in items],
    )


@router.get("/filters", response_model=schemas.FiltersOut)
def get_filters(db: Session = Depends(get_db)):
    """Distinct values for each filterable field (for UI dropdowns)."""

    def distinct(col):
        rows = db.query(col).distinct().order_by(col).all()
        return sorted(r[0] for r in rows if r[0] is not None and r[0] != "")

    return schemas.FiltersOut(
        designations=distinct(models.Employee.designation_name),
        subjects=distinct(models.Employee.subject_name),
        statuses=distinct(models.Employee.status_name),
        genders=distinct(models.Employee.gender),
        verification_statuses=distinct(models.Employee.verification_status),
    )


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total_employees = db.query(func.count(models.Employee.id)).scalar() or 0
    total_institutions = db.query(func.count(models.Institution.id)).scalar() or 0

    by_designation_rows = (
        db.query(models.Employee.designation_name, func.count(models.Employee.id))
        .group_by(models.Employee.designation_name)
        .order_by(func.count(models.Employee.id).desc())
        .all()
    )
    by_designation = [
        schemas.DesignationCount(designation_name=d, count=c) for d, c in by_designation_rows
    ]

    by_gender_rows = (
        db.query(models.Employee.gender, func.count(models.Employee.id))
        .group_by(models.Employee.gender)
        .order_by(func.count(models.Employee.id).desc())
        .all()
    )
    by_gender = [{"gender": g, "count": c} for g, c in by_gender_rows]

    by_status_rows = (
        db.query(models.Employee.status_name, func.count(models.Employee.id))
        .group_by(models.Employee.status_name)
        .order_by(func.count(models.Employee.id).desc())
        .all()
    )
    by_status = [{"status": s, "count": c} for s, c in by_status_rows]

    top_institutions_rows = (
        db.query(models.Institution.eiin, func.count(models.Employee.id))
        .outerjoin(models.Employee)
        .group_by(models.Institution.eiin)
        .order_by(func.count(models.Employee.id).desc())
        .limit(20)
        .all()
    )
    top_institutions = [{"eiin": e, "count": c} for e, c in top_institutions_rows]

    return schemas.StatsOut(
        total_employees=total_employees,
        total_institutions=total_institutions,
        by_designation=by_designation,
        by_gender=by_gender,
        by_status=by_status,
        top_institutions=top_institutions,
    )
