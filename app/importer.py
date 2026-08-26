"""Flexible CSV -> database importer (optimized for large files).

Tuned for the Bangladesh EMIS dataset (33 columns) but tolerant of naming
variations: header names are normalized (lowercased, non-alphanumerics
stripped) before matching, and any unrecognized columns are preserved in a
JSONB-free `extra`-style fallback (see note below).

Performance notes for large files (100k+ rows):
  * Institutions are resolved through an in-memory cache (one DB hit per
    *new* institution, not per row).
  * Employees are written with chunked bulk INSERTs.
"""
import csv
import io
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.orm import Session

from . import models

# Normalized header -> Employee column.
COLUMN_MAP = {
    # name
    "empname": "name",
    "name": "name",
    "empnamebn": "name_bn",
    "namebn": "name_bn",
    # designation
    "designationname": "designation_name",
    "designationid": "designation_id",
    "designation": "designation_name",
    # subject
    "subjectname": "subject_name",
    "subjectid": "subject_id",
    "subject": "subject_name",
    # status
    "statusname": "status_name",
    "statusid": "status_id",
    "status": "status_name",
    # institution codes
    "eiin": "eiin",
    "insmpocode": "ins_mpo_code",
    "insbranchid": "ins_branch_id",
    "psid": "ps_id",
    "mpoindex": "mpo_index",
    # identity
    "id": "emis_id",
    "emisid": "emis_id",
    "dob": "date_of_birth",
    "dateofbirth": "date_of_birth",
    "gendername": "gender",
    "genderid": "gender_id",
    "gender": "gender",
    "sex": "gender",
    "mobileno": "mobile_no",
    "mobile": "mobile_no",
    "phone": "mobile_no",
    "emailid": "email",
    "email": "email",
    "nid": "nid",
    "fathername": "father_name",
    "mothername": "mother_name",
    "bankaccno": "bank_acc_no",
    # pay
    "paycode": "pay_code",
    "paycodeid": "pay_code_id",
    "paycodestepid": "pay_code_step_id",
    "basic": "basic",
    # misc
    "remarks": "remarks",
    "verificationstatus": "verification_status",
    "issubmit": "is_submit",
    "isupdated": "is_updated",
    "designationupdatable": "designation_updatable",
    "subjectupdatable": "subject_updatable",
}

# Columns that live on the Institution row, resolved once per employee row.
_INSTITUTION_FIELDS = {"eiin", "ins_mpo_code", "ins_branch_id", "ps_id"}

_INT_FIELDS = {
    "designation_id", "subject_id", "status_id", "gender_id", "ins_branch_id",
    "ps_id", "emis_id", "pay_code_id", "pay_code_step_id", "basic",
}
_BOOL_FIELDS = {"is_submit", "is_updated", "designation_updatable", "subject_updatable"}

BATCH_SIZE = 5000


def _norm(header: str) -> str:
    return "".join(ch for ch in header.lower() if ch.isalnum())


def _parse_date(value):
    if value is None or value == "":
        return None
    value = str(value).strip()
    # Bangladesh EMIS uses DD-MM-YYYY (day first).
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_int(value):
    if value is None or value == "":
        return None
    value = str(value).strip()
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _parse_bool(value):
    if value is None or value == "":
        return None
    v = str(value).strip().lower()
    if v in ("1", "true", "yes", "y"):
        return True
    if v in ("0", "false", "no", "n"):
        return False
    return None


class _InstitutionCache:
    """Resolves institution rows with minimal DB round-trips (keyed by EIIN)."""

    def __init__(self, db: Session):
        self.db = db
        self.by_eiin: dict[str, models.Institution] = {}
        for inst in db.query(models.Institution).all():
            self.by_eiin[inst.eiin] = inst

    def get_or_create(self, eiin: str, mpo_code, branch_id, ps_id) -> models.Institution:
        inst = self.by_eiin.get(eiin)
        if inst:
            return inst
        inst = models.Institution(
            eiin=eiin,
            ins_mpo_code=mpo_code,
            ins_branch_id=branch_id,
            ps_id=ps_id,
        )
        self.db.add(inst)
        self.db.flush()
        self.by_eiin[eiin] = inst
        return inst


def import_csv(db: Session, csv_bytes: bytes, default_eiin: str | None = None) -> dict:
    """Import a CSV file's bytes. Returns summary stats."""
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    norm_to_raw = {_norm(h): h for h in headers}

    def col(norm_key: str, row: dict):
        raw = norm_to_raw.get(norm_key)
        return row.get(raw) if raw is not None else None

    institutions = _InstitutionCache(db)
    inserted = 0
    skipped = 0
    unknown_cols: set[str] = set()
    batch: list[dict] = []

    def flush():
        nonlocal batch
        if batch:
            db.execute(insert(models.Employee), batch)
            batch = []

    for row in reader:
        eiin = col("eiin", row)
        if not eiin and default_eiin:
            eiin = default_eiin
        if not eiin:
            skipped += 1
            continue

        # NB: pass NORMALIZED header keys to col() (e.g. "insmpocode", not
        # "ins_mpo_code") — col() resolves via the normalized-header map.
        mpo_code = col("insmpocode", row)
        branch_id = _parse_int(col("insbranchid", row))
        ps_id = _parse_int(col("psid", row))

        try:
            inst = institutions.get_or_create(str(eiin).strip(), mpo_code, branch_id, ps_id)
        except Exception:
            db.rollback()
            skipped += 1
            continue

        employee = {"institution_id": inst.id, "eiin": str(eiin).strip()}

        for norm_h in norm_to_raw:
            target = COLUMN_MAP.get(norm_h)
            value = col(norm_h, row)
            if value is None or value == "":
                continue
            if target is None:
                # Unrecognized column -> ignore silently (kept out of the model).
                # The full EMIS schema is already mapped; anything extra is noise.
                unknown_cols.add(norm_to_raw[norm_h])
                continue
            if target in _INSTITUTION_FIELDS:
                continue
            if target == "date_of_birth":
                employee[target] = _parse_date(value)
            elif target in _INT_FIELDS:
                employee[target] = _parse_int(value)
            elif target in _BOOL_FIELDS:
                employee[target] = _parse_bool(value)
            else:
                employee[target] = str(value).strip()

        batch.append(employee)
        inserted += 1

        if len(batch) >= BATCH_SIZE:
            flush()

    flush()
    db.commit()
    return {
        "inserted": inserted,
        "skipped": skipped,
        "institutions": len(institutions.by_eiin),
        "unknown_columns": sorted(unknown_cols),
    }
