"""Pydantic schemas for request/response serialization."""
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_id: int
    school_name: Optional[str] = None
    school_code: Optional[str] = None
    student_code: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    grade: Optional[str] = None
    section: Optional[str] = None
    admission_date: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    status: Optional[str] = None
    extra: Optional[dict[str, Any]] = None


class PaginatedStudents(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: list[StudentOut]


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    city: Optional[str] = None
    state: Optional[str] = None
    student_count: int = 0


class ApiKeyCreate(BaseModel):
    name: str
    school_id: Optional[int] = None


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    key_prefix: str
    school_id: Optional[int] = None
    active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


class ApiKeyCreated(ApiKeyOut):
    # The full key is returned exactly once, at creation time.
    key: Optional[str] = None


class GradeCount(BaseModel):
    grade: Optional[str] = None
    count: int


class StatsOut(BaseModel):
    total_students: int
    total_schools: int
    by_grade: list[GradeCount]
    by_school: list[dict[str, Any]]
