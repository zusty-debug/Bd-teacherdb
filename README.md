# Student Records API

A centralized, multi-school **student records API** built with FastAPI + PostgreSQL.
Query any student's record through a clean REST API, protected by a two-tier
key system (a single **master key** for admins + per-client **API keys**).

## Features

- **Multi-tenant** — many schools in one database; every student belongs to a school.
- **Two-tier auth**
  - `X-Master-Key` → admin endpoints (create / list / revoke API keys).
  - `X-API-Key` → all data endpoints.
- **Query endpoints** — search, filter (school, grade, section, gender, status),
  sort, and paginate student records.
- **Flexible CSV import** — recognizes common column names, stashes unknown
  columns in a JSONB `extra` field (nothing is lost).
- **Auto-generated docs** — interactive Swagger UI at `/docs`.

---

## Quick start (local)

```bash
# 1. Create a virtualenv + install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env          # edit DATABASE_URL + MASTER_KEY

# 3. (Optional) generate sample data
python -m scripts.generate_sample_csv --rows 20000 --out sample_students.csv

# 4. Import a CSV into the database
python -m scripts.import_csv sample_students.csv

# 5. Run the API
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs to explore the API interactively.

---

## Authentication flow

1. **Create an API key** (requires the master key):
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/keys \
        -H "X-Master-Key: YOUR_MASTER_KEY" \
        -H "Content-Type: application/json" \
        -d '{"name": "frontend-app"}'
   ```
   → Response includes the full key **once** (save it; only its hash is stored).

2. **Use the API key** on data endpoints:
   ```bash
   curl http://localhost:8000/api/v1/students?search=Aarav \
        -H "X-API-Key: sk_..."
   ```

3. **Revoke / re-enable** a key:
   ```bash
   curl -X DELETE http://localhost:8000/api/v1/admin/keys/{id} -H "X-Master-Key: ..."
   curl -X POST   http://localhost:8000/api/v1/admin/keys/{id}/toggle -H "X-Master-Key: ..."
   ```

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| GET | `/api/v1/students` | API key | List students (search/filter/sort/page) |
| GET | `/api/v1/students/{id}` | API key | Single student |
| GET | `/api/v1/schools` | API key | List schools + counts |
| GET | `/api/v1/stats` | API key | Aggregates (by grade, by school) |
| POST | `/api/v1/admin/keys` | Master key | Create an API key |
| GET | `/api/v1/admin/keys` | Master key | List API keys |
| DELETE | `/api/v1/admin/keys/{id}` | Master key | Revoke an API key |
| POST | `/api/v1/admin/keys/{id}/toggle` | Master key | Enable/disable a key |

### Query parameters for `GET /api/v1/students`

`search`, `school_id`, `school_code`, `grade`, `section`, `gender`, `status`,
`page` (default 1), `per_page` (default 50, max 500), `sort` (id, first_name,
last_name, grade, date_of_birth, admission_date, created_at, student_code),
`order` (asc/desc).

---

## CSV import

```bash
python -m scripts.import_csv path/to/data.csv --default-school "My School"
```

- Header names are normalized (`First Name` → `first_name`), so common naming
  variations are matched automatically (see `app/importer.py` for the full map).
- A `school_name` / `school_code` column groups rows into schools; schools are
  auto-created on first sight.
- Columns that don't match a known field are preserved in the student's `extra`
  JSONB object — nothing is lost.

---

## Deployment (Render)

1. Push this repo to GitHub.
2. Render → **New** → **Blueprint** → select the repo.
   - `render.yaml` provisions the web service **and** a managed Postgres DB,
     sets `DATABASE_URL`, and auto-generates `MASTER_KEY`.
3. After deploy, find your master key under the service's **Environment** tab
   (`MASTER_KEY`).
4. Seed the DB: run `python -m scripts.import_csv ...` (or a one-off shell) to
   load your real CSV, then create an API key via `/api/v1/admin/keys`.

---

## Project layout

```
student-api/
├── app/
│   ├── main.py            # FastAPI app + lifespan
│   ├── config.py          # env config
│   ├── database.py        # engine / session / Base
│   ├── models.py          # School, Student, ApiKey
│   ├── schemas.py         # Pydantic schemas
│   ├── security.py        # master key + API key auth
│   ├── importer.py        # flexible CSV importer
│   └── routers/
│       ├── health.py
│       ├── students.py
│       ├── schools.py     # + /stats
│       └── admin.py       # key management
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
TEST_DATABASE_URL=postgresql+psycopg2://studentapi:studentapi@localhost:5432/student_api_test \
  python -m pytest -q
# (omit TEST_DATABASE_URL to use a local SQLite test.db)
```
