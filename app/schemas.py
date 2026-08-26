"""Pydantic schemas for request/response serialization."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    eiin: str
    emis_id: Optional[int] = None
    name: Optional[str] = None
    name_bn: Optional[str] = None
    designation_name: Optional[str] = None
    designation_id: Optional[int] = None
    subject_name: Optional[str] = None
    subject_id: Optional[int] = None
    status_name: Optional[str] = None
    status_id: Optional[int] = None
    mpo_index: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    gender_id: Optional[int] = None
    mobile_no: Optional[str] = None
    email: Optional[str] = None
    nid: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    bank_acc_no: Optional[str] = None
    pay_code: Optional[str] = None
    pay_code_id: Optional[int] = None
    pay_code_step_id: Optional[int] = None
    basic: Optional[int] = None
    remarks: Optional[str] = None
    verification_status: Optional[str] = None
    is_submit: Optional[bool] = None
    is_updated: Optional[bool] = None
    designation_updatable: Optional[bool] = None
    subject_updatable: Optional[bool] = None


class PaginatedEmployees(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: list[EmployeeOut]


class InstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eiin: str
    ins_mpo_code: Optional[str] = None
    ins_branch_id: Optional[int] = None
    ps_id: Optional[int] = None
    employee_count: int = 0


class ApiKeyCreate(BaseModel):
    name: str
    institution_id: Optional[int] = None


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    key_prefix: str
    institution_id: Optional[int] = None
    active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


class ApiKeyCreated(ApiKeyOut):
    # The full key is returned exactly once, at creation time.
    key: Optional[str] = None


class DesignationCount(BaseModel):
    designation_name: Optional[str] = None
    count: int


class StatsOut(BaseModel):
    total_employees: int
    total_institutions: int
    by_designation: list[DesignationCount]
    by_gender: list[dict]
    by_status: list[dict]
    top_institutions: list[dict]
