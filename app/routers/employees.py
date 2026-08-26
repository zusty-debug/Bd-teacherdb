"""Employee (teacher/staff) query endpoints (require a valid API key)."""
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import MAX_PER_PAGE
from ..database import get_db
from ..security import require_api_key

router = APIRouter(
    prefix="/api/v1/employees", tags=["employees"], dependencies=[Depends(require_api_key)]
)

_SORTABLE = {
    "id": models.Employee.id,
    "emis_id": models.Employee.emis_id,
    "name": models.Employee.name,
    "date_of_birth": models.Employee.date_of_birth,
    "designation_name": models.Employee.designation_name,
    "subject_name": models.Employee.subject_name,
    "status_name": models.Employee.status_name,
    "basic": models.Employee.basic,
    "created_at": models.Employee.created_at,
}


@router.get("", response_model=schemas.PaginatedEmployees)
def list_employees(
    search: Optional[str] = Query(default=None, description="Matches name, Bengali name, mobile, email, NID"),
    eiin: Optional[str] = Query(default=None, description="Institution EIIN code"),
    designation_name: Optional[str] = Query(default=None),
    subject_name: Optional[str] = Query(default=None),
    status_name: Optional[str] = Query(default=None),
    gender: Optional[str] = Query(default=None),
    verification_status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=MAX_PER_PAGE),
    sort: str = Query(default="id"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    q = db.query(models.Employee)

    if eiin:
        q = q.filter(models.Employee.eiin == eiin)
    if designation_name:
        q = q.filter(models.Employee.designation_name == designation_name)
    if subject_name:
        q = q.filter(models.Employee.subject_name == subject_name)
    if status_name:
        q = q.filter(models.Employee.status_name == status_name)
    if gender:
        q = q.filter(models.Employee.gender == gender)
    if verification_status:
        q = q.filter(models.Employee.verification_status == verification_status)
    if search:
        # lower(col) LIKE so Postgres uses pg_trgm GIN indexes.
        like = f"%{search.lower()}%"
        q = q.filter(
            or_(
                func.lower(models.Employee.name).like(like),
                func.lower(models.Employee.name_bn).like(like),
                func.lower(models.Employee.mobile_no).like(like),
                func.lower(models.Employee.email).like(like),
                func.lower(models.Employee.nid).like(like),
                func.lower(models.Employee.father_name).like(like),
            )
        )

    total = q.count()

    sort_col = _SORTABLE.get(sort, models.Employee.id)
    q = q.order_by(sort_col.asc() if order == "asc" else sort_col.desc())

    items = q.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, math.ceil(total / per_page)) if total else 1

    return schemas.PaginatedEmployees(
        total=total, page=page, per_page=per_page, pages=pages,
        items=[schemas.EmployeeOut.model_validate(s) for s in items],
    )


@router.get("/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp
