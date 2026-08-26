# EMIS Records API

A centralized, multi-institution **records API** built with FastAPI + PostgreSQL,
backed by the **Bangladesh EMIS dataset** (teachers/staff across ~19,000
educational institutions). Query any record through a clean REST API, protected
by a two-tier key system (a single **master key** for admins + per-client **API keys**).

> **Data note:** the source CSV contains *teacher/staff* records (`empName`,
> designation, subject, pay scale, …), keyed by institution **EIIN** code — not
> student records. The API models this as **Institutions → Employees**.

## Features

- **Multi-tenant** — ~19k institutions in one database; every employee belongs to an institution.
- **Two-tier auth**
  - `X-Master-Key` → admin endpoints (create / list / revoke API keys).
  - `X-API-Key` → all data endpoints.
- **Query endpoints** — full-text search (English *and* Bengali names, mobile, email, NID),
  filter (EIIN, designation, subject, status, gender, verification status),
  sort, and paginate records.
- **Fast search** — PostgreSQL `pg_trgm` indexes give ~millisecond name lookup
  over ~400k rows (including Bengali text).
- **Flexible CSV import** — normalized header matching; unknown columns ignored.
- **Auto-generated docs** — interactive Swagger UI at `/docs`.

---

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # edit DATABASE_URL + MASTER_KEY

# Import the CSV (creates tables + indexes automatically)
python -m scripts.import_csv /path/to/emis_full.csv

# Run the API
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs to explore interactively.

---

## Authentication flow

1. **Create an API key** (requires the master key):
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/keys \
        -H "X-Master-Key: YOUR_MASTER_KEY" \
        -H "Content-Type: application/json" \
        -d '{"name": "frontend-app"}'
   ```
   → Response includes the full key **once** (only its hash is stored).

2. **Use the API key** on data endpoints:
   ```bash
   curl "http://localhost:8000/api/v1/employees?search=ZAMAL" -H "X-API-Key: sk_..."
   ```

3. **Revoke / re-enable**:
   ```bash
   curl -X DELETE http://localhost:8000/api/v1/admin/keys/{id} -H "X-Master-Key: ..."
   curl -X POST   http://localhost:8000/api/v1/admin/keys/{id}/toggle -H "X-Master-Key: ..."
   ```

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| GET | `/api/v1/employees` | API key | List employees (search/filter/sort/page) |
| GET | `/api/v1/employees/{id}` | API key | Single employee record |
| GET | `/api/v1/institutions` | API key | List institutions + employee counts |
| GET | `/api/v1/stats` | API key | Aggregates (designation, gender, status, top institutions) |
| POST | `/api/v1/admin/keys` | Master key | Create an API key |
| GET | `/api/v1/admin/keys` | Master key | List API keys |
| DELETE | `/api/v1/admin/keys/{id}` | Master key | Revoke an API key |
| POST | `/api/v1/admin/keys/{id}/toggle` | Master key | Enable/disable a key |

### Query parameters for `GET /api/v1/employees`

`search`, `eiin`, `designation_name`, `subject_name`, `status_name`, `gender`,
`verification_status`, `page` (default 1), `per_page` (default 50, max 500),
`sort` (id, emis_id, name, date_of_birth, designation_name, subject_name,
status_name, basic, created_at), `order` (asc/desc).

---

## CSV import

```bash
python -m scripts.import_csv path/to/emis_full.csv
```

- Header names are normalized (`empName` → `name`, `designationName` →
  `designation_name`, …). See `app/importer.py` for the full map.
- Institutions are auto-created and keyed by the `eiin` column.
- `dob` is parsed as `DD-MM-YYYY` (Bangladesh convention), integer/bool fields
  are coerced safely, and unrecognized columns are skipped.

---

## Deployment (Render)

1. Push this repo to GitHub.
2. Render → **New** → **Blueprint** → select the repo.
   - `render.yaml` provisions the web service **and** a managed Postgres DB,
     sets `DATABASE_URL`, and auto-generates `MASTER_KEY`.
3. After deploy, find your master key under the service's **Environment** tab.
4. Seed the DB (one-off shell job): `python -m scripts.import_csv emis_full.csv`,
   then create an API key via `/api/v1/admin/keys`.

---

## Project layout

```
student-api/
├── app/
│   ├── main.py            # FastAPI app + lifespan
│   ├── config.py          # env config
│   ├── database.py        # engine / session / Base / pg_trgm indexes
│   ├── models.py          # Institution, Employee, ApiKey
│   ├── schemas.py         # Pydantic schemas
│   ├── security.py        # master key + API key auth
│   ├── importer.py        # bulk CSV importer
│   └── routers/
│       ├── health.py
│       ├── employees.py
│       ├── institutions.py  # + /stats
│       └── admin.py         # key management
├── scripts/
│   ├── generate_sample_csv.py
│   └── import_csv.py
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── render.yaml
└── requirements.txt
```

## Running the tests

```bash
# Uses a dedicated test DB (keeps dev data safe):
TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/test_db \
  python -m pytest -q
# (omit TEST_DATABASE_URL to use a local SQLite test.db)
```
