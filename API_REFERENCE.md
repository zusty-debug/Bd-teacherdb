# API Reference

Everything is accessed as **Base URL → API key → endpoint**.

## 1. Base URL

| Environment | Base URL |
|---|---|
| Local dev | `http://localhost:8000` |
| Production (Render) | `https://<your-service>.onrender.com` |

All data endpoints are under `/api/v1`.

## 2. Keys

Two kinds of keys, sent as **HTTP headers** on every request.

| Header | Key type | Used for |
|---|---|---|
| `X-API-Key: sk_...` | API key | All **data** endpoints (read access) |
| `X-Master-Key: ...` | Master key | **Admin** endpoints (manage API keys) |

- **Master key** is set once in the environment (`MASTER_KEY`) — held only by you.
- **API keys** are generated via the admin endpoint and handed to clients/apps.
- The full API key is shown **only once** at creation; only its hash is stored.

---

## 3. Endpoints

### Health (no key needed)
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |

### Employees (requires `X-API-Key`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/employees` | List/search employees (paginated) |
| GET | `/api/v1/employees/{id}` | Single employee record |

**Query params for `GET /employees`:**

| Param | Description |
|---|---|
| `search` | Full-text search across name, Bengali name, mobile, email, NID, father name |
| `eiin` | Filter by institution EIIN code |
| `designation_name` | e.g. `HEAD MASTER`, `ASSISTANT TEACHER` |
| `subject_name` | Subject taught |
| `status_name` | Bengali status, e.g. `কর্মরত` |
| `gender` | `Male` / `Female` / `Others` |
| `verification_status` | e.g. `Verification Completed` |
| `page` | Page number (default 1) |
| `per_page` | Rows per page (default 50, max 500) |
| `sort` | `id`, `emis_id`, `name`, `date_of_birth`, `designation_name`, `subject_name`, `status_name`, `basic`, `created_at` |
| `order` | `asc` / `desc` |

### Institutions (requires `X-API-Key`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/institutions` | List institutions + employee counts |
| GET | `/api/v1/institutions/{eiin}` | Single institution detail |
| GET | `/api/v1/institutions/{eiin}/employees` | Employees of one institution (paginated) |

**Query params for `GET /institutions`:** `search` (matches EIIN or MPO code).

**Query params for `GET /institutions/{eiin}/employees`:** `designation_name`, `status_name`, `page`, `per_page`.

### Stats & metadata (requires `X-API-Key`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/stats` | Totals + breakdowns (designation, gender, status, top institutions) |
| GET | `/api/v1/filters` | Distinct values for every filter field (for UI dropdowns) |

### Admin — API key management (requires `X-Master-Key`)
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/admin/keys` | Create an API key (returns full key once) |
| GET | `/api/v1/admin/keys` | List API keys |
| DELETE | `/api/v1/admin/keys/{id}` | Revoke an API key |
| POST | `/api/v1/admin/keys/{id}/toggle` | Enable / disable a key |

---

## 4. Examples

```bash
BASE="https://<your-service>.onrender.com"

# 1. Create an API key (master key required)
curl -X POST "$BASE/api/v1/admin/keys" \
     -H "X-Master-Key: YOUR_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name": "my-app"}'

# 2. Search employees (API key required)
curl "$BASE/api/v1/employees?search=ZAMAL&per_page=5" \
     -H "X-API-Key: sk_..."

# 3. All employees of one institution
curl "$BASE/api/v1/institutions/100005/employees" \
     -H "X-API-Key: sk_..."

# 4. Get a single record
curl "$BASE/api/v1/employees/2" -H "X-API-Key: sk_..."

# 5. Aggregate stats
curl "$BASE/api/v1/stats" -H "X-API-Key: sk_..."

# 6. Filter dropdown values (for a UI)
curl "$BASE/api/v1/filters" -H "X-API-Key: sk_..."
```
