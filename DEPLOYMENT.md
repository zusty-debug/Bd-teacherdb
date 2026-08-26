# Deployment Guide — Render (web service) + Neon (free Postgres)

This setup keeps the **API on Render's free tier** and the **database on Neon's
free Postgres** (which never expires — unlike Render's free Postgres, which is
deleted after 30 days).

---

## Why Neon instead of Render's Postgres?

| | Render free Postgres | Neon free Postgres |
|---|---|---|
| Expiry | **Deleted after 30 days** | Permanent |
| Storage | 1 GB | 0.5 GB |
| Our data | 335 MB | Fits (~165 MB headroom) |

---

## 1. Create a free Neon database

1. Go to https://neon.tech → **Sign up** with GitHub.
2. **Create a project** (any name, e.g. `bd-teacherdb`). It auto-creates a
   `neondb` database.
3. On the project page, click **Connect** → copy the **Pooled connection
   string** (or the standard one). It looks like:
   ```
   postgresql://neondb_owner:xxxxxxx@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require
   ```
   Save this string — you'll paste it into Render.

---

## 2. Point Render at Neon

1. On Render, open the `emis-records-api` service.
2. Go to **Environment** tab.
3. If a `DATABASE_URL` entry exists (auto-created by the old blueprint),
   **delete it**.
4. **Add Environment Variable**: key `DATABASE_URL`, value = your Neon
   connection string.
5. Confirm `MASTER_KEY` is present (Render generated it). If you want to use
   your own, replace it — but keep it secret.
6. **Save Changes** → Render redeploys automatically (~2–3 min).

> The app already handles Neon's `postgresql://` scheme and `?sslmode=require`
> automatically (see `app/config.py`).

---

## 3. Delete the (now unused) Render Postgres

1. On Render, open the `emis-records-db` database.
2. **Settings** → scroll down → **Delete Database**.
   - If the button is disabled, delete the web service's old `DATABASE_URL`
     first (done in step 2), or delete the service's link to the DB.

---

## 4. Load your data into Neon

1. In `emis-records-api` → **Shell** tab (the shell inherits `DATABASE_URL`).
2. Run:
   ```bash
   curl -o emis_full.csv https://files.catbox.moe/54n9at.csv
   python -m scripts.import_csv emis_full.csv
   ```
3. Wait ~3–5 min. Expect:
   ```
   inserted: 396970
   skipped: 0
   institutions: 19106
   unknown_columns: []
   ```

---

## 5. Create an API key + test

```bash
# Create a key (master key from Render Environment tab)
curl -X POST https://<your-url>.onrender.com/api/v1/admin/keys \
     -H "X-Master-Key: YOUR_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name": "my-first-app"}'

# Test a query
curl "https://<your-url>.onrender.com/api/v1/employees?search=ZAMAL&per_page=3" \
     -H "X-API-Key: sk_..."
```

Full endpoint reference: `API_REFERENCE.md`.

---

## Notes & gotchas

- **Cold start**: free Render web service sleeps after 15 min idle; the first
  request after sleep takes ~1 min. Neon also suspends when idle (cold start on
  first query). This is normal on free tiers.
- **Storage headroom**: our data is ~335 MB of Neon's 500 MB. If you later add
  more data and approach the limit, we can trim redundant indexes.
- **Neon suspend**: Neon's free compute suspends after ~5 min idle and restarts
  on the next connection (a few seconds). Fine for testing.

## Troubleshooting

- **"Can't load plugin sqlalchemy.dialects:postgres"** → already fixed in
  `app/config.py`.
- **Connection refused / SSL error to Neon** → make sure the `DATABASE_URL`
  includes `?sslmode=require` (it's in Neon's copied string by default).
- **Import too slow / timeouts** → run the import from the Render shell (same
  region network), or from your own machine.
