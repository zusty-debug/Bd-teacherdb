"""Institutions listing + aggregate stats (require a valid API key)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
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
