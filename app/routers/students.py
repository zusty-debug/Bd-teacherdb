"""Student query endpoints (require a valid API key)."""
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_api_key
from ..config import MAX_PER_PAGE

router = APIRouter(prefix="/api/v1/students", tags=["students"], dependencies=[Depends(require_api_key)])

_SORTABLE = {
    "id": models.Student.id,
    "student_code": models.Student.student_code,
    "first_name": models.Student.first_name,
    "last_name": models.Student.last_name,
    "date_of_birth": models.Student.date_of_birth,
    "admission_date": models.Student.admission_date,
    "grade": models.Student.grade,
    "created_at": models.Student.created_at,
}


@router.get("", response_model=schemas.PaginatedStudents)
def list_students(
    search: Optional[str] = Query(default=None, description="Matches name, student code, or email"),
    school_id: Optional[int] = Query(default=None),
    school_code: Optional[str] = Query(default=None),
    grade: Optional[str] = Query(default=None),
    section: Optional[str] = Query(default=None),
    gender: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=MAX_PER_PAGE),
    sort: str = Query(default="id"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    q = db.query(models.Student)

    if school_id is not None:
        q = q.filter(models.Student.school_id == school_id)
    if school_code:
        q = q.join(models.School).filter(models.School.code == school_code)
    if grade:
        q = q.filter(models.Student.grade == grade)
    if section:
        q = q.filter(models.Student.section == section)
    if gender:
        q = q.filter(models.Student.gender == gender)
    if status:
        q = q.filter(models.Student.status == status)
    if search:
        # Use lower(col) LIKE '%term%' so Postgres can use the pg_trgm GIN
        # indexes created in database.setup_postgres_indexes().
        like = f"%{search.lower()}%"
        q = q.filter(
            or_(
                func.lower(models.Student.first_name).like(like),
                func.lower(models.Student.last_name).like(like),
                func.lower(models.Student.student_code).like(like),
                func.lower(models.Student.email).like(like),
            )
        )

    total = q.count()

    sort_col = _SORTABLE.get(sort, models.Student.id)
    q = q.order_by(sort_col.asc() if order == "asc" else sort_col.desc())

    items = q.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, math.ceil(total / per_page)) if total else 1

    return schemas.PaginatedStudents(
        total=total, page=page, per_page=per_page, pages=pages,
        items=[schemas.StudentOut.model_validate(s) for s in items],
    )


@router.get("/{student_id}", response_model=schemas.StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
