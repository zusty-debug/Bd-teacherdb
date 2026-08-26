"""SQLAlchemy ORM models: Institution, Employee, ApiKey.

Modeled on the Bangladesh EMIS (Education Management Information System)
dataset: educational institutions (keyed by EIIN code) and the teachers/staff
("employees") who work at them.
"""
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
from sqlalchemy.orm import relationship

from .database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True)
    eiin = Column(String(32), unique=True, nullable=False, index=True)  # institution ID
    ins_mpo_code = Column(String(64), nullable=True)
    ins_branch_id = Column(Integer, nullable=True)
    ps_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employees = relationship("Employee", back_populates="institution")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    eiin = Column(String(32), nullable=False, index=True)  # denormalized for fast filtering

    # EMIS source record id (the dataset's `id` column).
    emis_id = Column(Integer, nullable=True, index=True)

    name = Column(String(255), nullable=True, index=True)          # empName (English)
    name_bn = Column(String(255), nullable=True)                    # empNameBn (Bengali)

    designation_name = Column(String(128), nullable=True, index=True)
    designation_id = Column(Integer, nullable=True)
    subject_name = Column(String(128), nullable=True, index=True)
    subject_id = Column(Integer, nullable=True)

    status_name = Column(String(64), nullable=True, index=True)     # Bengali, e.g. কর্মরত
    status_id = Column(Integer, nullable=True)

    mpo_index = Column(String(64), nullable=True, index=True)

    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(32), nullable=True, index=True)
    gender_id = Column(Integer, nullable=True)

    mobile_no = Column(String(32), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    nid = Column(String(64), nullable=True, index=True)             # national ID

    father_name = Column(String(128), nullable=True)
    mother_name = Column(String(128), nullable=True)
    bank_acc_no = Column(String(64), nullable=True)

    pay_code = Column(String(64), nullable=True)
    pay_code_id = Column(Integer, nullable=True)
    pay_code_step_id = Column(Integer, nullable=True)
    basic = Column(Integer, nullable=True)                          # basic salary

    remarks = Column(Text, nullable=True)
    verification_status = Column(String(64), nullable=True, index=True)

    is_submit = Column(Boolean, nullable=True)
    is_updated = Column(Boolean, nullable=True)
    designation_updatable = Column(Boolean, nullable=True)
    subject_updatable = Column(Boolean, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    institution = relationship("Institution", back_populates="employees")

    __table_args__ = (
        Index("ix_employees_institution_designation", "institution_id", "designation_name"),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)  # human label, e.g. "Frontend app"
    key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256
    key_prefix = Column(String(16), nullable=False, index=True)  # for display only
    # Optional future scoping: bind a key to a single institution (null = all).
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
