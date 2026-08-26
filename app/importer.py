"""Flexible CSV -> database importer (optimized for large files).

Reads any CSV, maps recognized columns to Student/School fields, and stashes
unrecognized columns in the Student.extra JSONB column. Header names are
normalized (lowercased, non-alphanumerics stripped) before matching, so
"First Name", "first_name", and "FIRSTNAME" all map to `first_name`.

Performance notes for large files (100k+ rows):
  * Schools are resolved through an in-memory cache (one DB hit per *new*
    school, not per row).
  * Students are written with chunked bulk INSERTs.
"""
import csv
import io
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.orm import Session

from . import models

# Normalized header -> Student column. School name/code are resolved to School rows.
COLUMN_MAP = {
    "studentid": "student_code",
    "studentcode": "student_code",
    "rollno": "student_code",
    "rollnumber": "student_code",
    "admissionno": "student_code",
    "admissionnumber": "student_code",
    "enrollmentno": "student_code",
    "registrationno": "student_code",
    "firstname": "first_name",
    "lastname": "last_name",
    "name": None,  # handled specially -> split into first/last name
    "fullname": None,
    "dateofbirth": "date_of_birth",
    "dob": "date_of_birth",
    "birthdate": "date_of_birth",
    "gender": "gender",
    "sex": "gender",
    "grade": "grade",
    "class": "grade",
    "classname": "grade",
    "standard": "grade",
    "section": "section",
    "admissiondate": "admission_date",
    "dateofadmission": "admission_date",
    "email": "email",
    "emailaddress": "email",
    "phone": "phone",
    "phoneno": "phone",
    "mobileno": "phone",
    "contact": "phone",
    "address": "address",
    "guardianname": "guardian_name",
    "fathername": "guardian_name",
    "parentname": "guardian_name",
    "guardianphone": "guardian_phone",
    "fatherphone": "guardian_phone",
    "status": "status",
    "schoolid": "school_id",
    "school": "school_name",
    "schoolname": "school_name",
    "schoolcode": "school_code",
}

# School-level fields are resolved once per row and must not land in `extra`.
_SCHOOL_LEVEL = {"school_name", "school_code", "school_id"}
_IGNORED = {"", "id", "sno", "srno", "serialno", "slno"}

BATCH_SIZE = 5000


def _norm(header: str) -> str:
    return "".join(ch for ch in header.lower() if ch.isalnum())


def _parse_date(value):
    if value is None or value == "":
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


class _SchoolCache:
    """Resolves school rows with minimal DB round-trips."""

    def __init__(self, db: Session):
        self.db = db
        self.by_code: dict[str, models.School] = {}
        self.by_name: dict[str, models.School] = {}
        for s in db.query(models.School).all():
            self.by_code[s.code] = s
            self.by_name[s.name] = s

    def get_or_create(self, name: str, code: str | None) -> models.School:
        if code and code in self.by_code:
            return self.by_code[code]
        if name in self.by_name:
            return self.by_name[name]
        school = models.School(name=name, code=code or f"school-{abs(hash(name)) % 10**8}")
        self.db.add(school)
        self.db.flush()  # assign id
        self.by_code[school.code] = school
        self.by_name[school.name] = school
        return school


def import_csv(db: Session, csv_bytes: bytes, default_school_name: str = "Default School") -> dict:
    """Import a CSV file's bytes. Returns summary stats."""
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    norm_to_raw = {_norm(h): h for h in headers}

    def col(norm_key: str, row: dict):
        raw = norm_to_raw.get(norm_key)
        return row.get(raw) if raw is not None else None

    schools = _SchoolCache(db)
    inserted = 0
    skipped = 0
    unknown_cols: set[str] = set()
    batch: list[dict] = []

    def flush():
        nonlocal batch
        if batch:
            db.execute(insert(models.Student), batch)
            batch = []

    for row in reader:
        # --- resolve school ---
        school_name = col("schoolname", row) or col("school", row) or default_school_name
        school_code = col("schoolcode", row)
        if not school_name and not school_code:
            school_name = default_school_name
        try:
            school = schools.get_or_create(school_name, school_code)
        except Exception:
            db.rollback()
            skipped += 1
            continue

        # --- build student ---
        extra: dict = {}
        student = {"school_id": school.id}

        for norm_h in norm_to_raw:
            target = COLUMN_MAP.get(norm_h, "__unknown__")
            value = col(norm_h, row)
            if value is None or value == "":
                continue
            if target == "__unknown__":
                if norm_h in _IGNORED:
                    continue
                raw = norm_to_raw[norm_h]
                unknown_cols.add(raw)
                extra[raw] = value
                continue
            if target in _SCHOOL_LEVEL:
                continue
            if target is None:  # "name" / "fullname"
                if norm_h == "name":
                    parts = str(value).strip().split(None, 1)
                    student["first_name"] = parts[0] if parts else None
                    student["last_name"] = parts[1] if len(parts) > 1 else None
                continue
            if target in ("date_of_birth", "admission_date"):
                student[target] = _parse_date(value)
                continue
            student[target] = str(value).strip()

        student["extra"] = extra or None
        batch.append(student)
        inserted += 1

        if len(batch) >= BATCH_SIZE:
            flush()

    flush()
    db.commit()
    return {"inserted": inserted, "skipped": skipped, "unknown_columns": sorted(unknown_cols)}
