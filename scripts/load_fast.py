"""Fast loader: streams the CSV into Postgres via COPY (single-pass, no
per-row round-trips). ~10-20x faster than ORM bulk inserts over the network.

Usage:
    DATABASE_URL='postgresql://...' python -m scripts.load_fast /path/to/file.csv
"""
import argparse
import csv
import io
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg2  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.importer import _parse_bool, _parse_date, _parse_int  # noqa: E402

INST_COLS = ["eiin", "ins_mpo_code", "ins_branch_id", "ps_id"]

EMP_COLS = [
    "institution_id", "eiin", "emis_id", "name", "name_bn", "designation_name",
    "designation_id", "subject_name", "subject_id", "status_name", "status_id",
    "mpo_index", "date_of_birth", "gender", "gender_id", "mobile_no", "email",
    "nid", "father_name", "mother_name", "bank_acc_no", "pay_code",
    "pay_code_id", "pay_code_step_id", "basic", "remarks", "verification_status",
    "is_submit", "is_updated", "designation_updatable", "subject_updatable",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    args = ap.parse_args()

    # Ensure schema exists
    Base.metadata.create_all(bind=engine)

    raw_url = engine.url.render_as_string(hide_password=False)
    # psycopg2.connect expects a plain postgresql:// or postgres:// DSN, not
    # SQLAlchemy's postgresql+psycopg2:// driver-prefixed form.
    raw_url = raw_url.replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(raw_url)
    conn.autocommit = True
    cur = conn.cursor()

    # ---- Pass 1: collect distinct institutions ----
    inst_rows: dict[str, tuple] = {}  # eiin -> (eiin, mpo, branch, ps)
    with open(args.csv_path, encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eiin = (row.get("eiin") or "").strip()
            if not eiin:
                continue
            if eiin not in inst_rows:
                inst_rows[eiin] = (
                    eiin,
                    (row.get("insMpoCode") or "").strip() or None,
                    _parse_int(row.get("insBranchId")),
                    _parse_int(row.get("psID")),
                )

    print(f"Distinct institutions: {len(inst_rows)}")

    # COPY institutions
    buf = io.StringIO()
    w = csv.writer(buf)
    for v in inst_rows.values():
        w.writerow(v)
    buf.seek(0)
    cur.copy_expert(
        f"COPY institutions ({','.join(INST_COLS)}) FROM STDIN WITH (FORMAT csv)",
        buf,
    )
    print("Institutions loaded.")

    # Fetch eiin -> id
    cur.execute("SELECT eiin, id FROM institutions")
    eiin_to_id = {e: i for e, i in cur.fetchall()}

    # ---- Pass 2: stream employees ----
    total = 0
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", newline="") as tmp:
        w = csv.writer(tmp)
        with open(args.csv_path, encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                eiin = (row.get("eiin") or "").strip()
                if not eiin:
                    continue
                inst_id = eiin_to_id[eiin]
                w.writerow([
                    inst_id,
                    eiin,
                    _parse_int(row.get("id")),
                    (row.get("empName") or "").strip() or None,
                    (row.get("empNameBn") or "").strip() or None,
                    (row.get("designationName") or "").strip() or None,
                    _parse_int(row.get("designationId")),
                    (row.get("subjectName") or "").strip() or None,
                    _parse_int(row.get("subjectId")),
                    (row.get("statusName") or "").strip() or None,
                    _parse_int(row.get("statusId")),
                    (row.get("mpoIndex") or "").strip() or None,
                    _parse_date(row.get("dob")),
                    (row.get("genderName") or "").strip() or None,
                    _parse_int(row.get("genderId")),
                    (row.get("mobileNo") or "").strip() or None,
                    (row.get("emailId") or "").strip() or None,
                    (row.get("nid") or "").strip() or None,
                    (row.get("fatherName") or "").strip() or None,
                    (row.get("motherName") or "").strip() or None,
                    (row.get("bankAccNo") or "").strip() or None,
                    (row.get("payCode") or "").strip() or None,
                    _parse_int(row.get("payCodeId")),
                    _parse_int(row.get("payCodeStepId")),
                    _parse_int(row.get("basic")),
                    (row.get("remarks") or "").strip() or None,
                    (row.get("verificationStatus") or "").strip() or None,
                    _parse_bool(row.get("isSubmit")),
                    _parse_bool(row.get("isUpdated")),
                    _parse_bool(row.get("designationUpdatable")),
                    _parse_bool(row.get("subjectUpdatable")),
                ])
                total += 1
        tmp.seek(0)
        cur.copy_expert(
            f"COPY employees ({','.join(EMP_COLS)}) FROM STDIN WITH (FORMAT csv)",
            tmp,
        )
    print(f"Employees loaded: {total}")

    # Trigram indexes for fast search (do this last)
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        for col in ("name", "name_bn", "mobile_no", "email", "nid", "father_name"):
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS ix_employees_{col}_trgm "
                f"ON employees USING gin (lower({col}) gin_trgm_ops)"
            )
        print("Search indexes created.")
    except Exception as e:
        print(f"WARN: could not create trigram indexes: {e}")

    cur.close()
    conn.close()
    print("DONE.")


if __name__ == "__main__":
    main()
