"""Schools listing + aggregate stats (require a valid API key)."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import require_api_key

router = APIRouter(prefix="/api/v1", tags=["schools"], dependencies=[Depends(require_api_key)])


@router.get("/schools", response_model=list[schemas.SchoolOut])
def list_schools(db: Session = Depends(get_db)):
    rows = (
        db.query(models.School, func.count(models.Student.id).label("student_count"))
        .outerjoin(models.Student)
        .group_by(models.School.id)
        .order_by(models.School.name)
        .all()
    )
    return [
        schemas.SchoolOut(
            id=s.id, name=s.name, code=s.code, city=s.city, state=s.state,
            student_count=student_count,
        )
        for s, student_count in rows
    ]


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total_students = db.query(func.count(models.Student.id)).scalar() or 0
    total_schools = db.query(func.count(models.School.id)).scalar() or 0

    by_grade_rows = (
        db.query(models.Student.grade, func.count(models.Student.id))
        .group_by(models.Student.grade)
        .order_by(models.Student.grade)
        .all()
    )
    by_grade = [schemas.GradeCount(grade=g, count=c) for g, c in by_grade_rows]

    by_school_rows = (
        db.query(models.School.id, models.School.name, func.count(models.Student.id))
        .outerjoin(models.Student)
        .group_by(models.School.id, models.School.name)
        .order_by(func.count(models.Student.id).desc())
        .all()
    )
    by_school = [
        {"school_id": sid, "school_name": name, "count": c} for sid, name, c in by_school_rows
    ]

    return schemas.StatsOut(
        total_students=total_students,
        total_schools=total_schools,
        by_grade=by_grade,
        by_school=by_school,
    )
