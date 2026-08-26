"""SQLAlchemy ORM models: School, Student, ApiKey."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .database import Base


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    city = Column(String(128), nullable=True)
    state = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    students = relationship("Student", back_populates="school", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)

    # External identifier from the source system (e.g. roll number / admission no).
    student_code = Column(String(64), nullable=True, index=True)

    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(32), nullable=True, index=True)
    grade = Column(String(32), nullable=True, index=True)
    section = Column(String(32), nullable=True)
    admission_date = Column(Date, nullable=True)

    email = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True)
    address = Column(Text, nullable=True)
    guardian_name = Column(String(128), nullable=True)
    guardian_phone = Column(String(32), nullable=True)

    status = Column(String(32), nullable=True, default="active", index=True)

    # Any source columns that don't map to a known field are preserved here.
    extra = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    school = relationship("School", back_populates="students")

    __table_args__ = (
        Index("ix_students_name", "first_name", "last_name"),
    )

    @property
    def school_name(self) -> str | None:
        return self.school.name if self.school else None

    @property
    def school_code(self) -> str | None:
        return self.school.code if self.school else None


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)  # human label, e.g. "Frontend app"
    key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256
    key_prefix = Column(String(16), nullable=False, index=True)  # for display only
    # Optional future scoping: bind a key to a single school (null = all schools).
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
