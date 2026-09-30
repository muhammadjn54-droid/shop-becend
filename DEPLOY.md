# Deployment

Django + DRF backend for the shop inventory app.

- Backend repository: `shop-becend` (this one)
- Frontend repository: `shop-of-` (React, talks to the backend over `/api/`)

## Why the database matters

### Vercel (serverless) — SQLite cannot work

Vercel runs each request in a **separate serverless instance** with its own
`/tmp`. A SQLite file in `/tmp` is therefore not shared and is deleted when
an instance recycles. Measured on production: one freshly registered user,
one valid token, 10 parallel requests:

```
8x HTTP 401 (user not found on this instance)
2x HTTP 200 (user found)
```

So accounts, products and sales disappear within minutes, and the same
product returns 200 or 404 depending on which instance answers. **On Vercel
you must set `DATABASE_URL` to a real PostgreSQL.** `settings.py` prints
`[CRITICAL]` at boot while it is missing.

### Render — SQLite is fine

Render runs **one long-running process**, not a fresh instance per request,
so SQLite behaves normally and no external database is required. Its
filesystem is still wiped on every redeploy, so either attach a Persistent
Disk or use PostgreSQL.

## Check what a deployment is actually using

```
GET /api/health/
```

```json
{
  "status": "ok",
  "db_engine": "django.db.backends.postgresql",
  "is_postgres": true,
  "database_url_set": true,
  "is_vercel": false,
  "is_render": true,
  "data_dir": null,
  "db_reachable": true,
  "instance": "3f9a1c22"
}
```

It never prints credentials, hosts or passwords. `instance` changes on every
serverless instance, so two parallel requests returning different values
proves requests are landing on different processes (the Vercel problem).

## Deploying to Render

`render.yaml` is a Blueprint, so nothing needs typing into a dashboard:

1. Render → **New → Blueprint** → select this repository → apply.
2. It sets the build command, the start command, `SECRET_KEY`, and
   `healthCheckPath: /api/health/`.
3. Optional: uncomment the `disk` block and `DATA_DIR` to keep data across
   redeploys, or set `DATABASE_URL` for PostgreSQL.

If you configure the service by hand instead, the two commands are:

```
build:  pip install -r requirements.txt && python manage.py collectstatic --noinput
start:  sh -c "python manage.py migrate --noinput && gunicorn shop_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120"
```

`migrate` must run before gunicorn: a brand new database has no tables and
every request would fail with `no such table: accounts_customuser`.

> A start command of `12` (a Python version typed into the wrong field)
> fails with `bash: line 1: 12: command not found`. The commands above live
> in the repository precisely so this cannot happen.

## Deploying to Vercel

`vercel.json` points at `shop_backend/wsgi.py`. Set `DATABASE_URL` to a
PostgreSQL connection string, otherwise the app runs on per-instance
`/tmp` SQLite and loses all data.

## Pointing the frontend at a deployment

In the frontend repository set `VITE_API_URL` (no trailing slash, **no
`/api` suffix** — the app appends `/api/...` itself):

```
VITE_API_URL=https://your-backend.onrender.com
```

It defaults to `https://shop-becend.vercel.app`, so nothing is required
while using the Vercel deployment.

## Tests

```bash
python manage.py test          # 59 tests
```

Covers barcode uniqueness and per-user isolation, concurrent sales
(no `database is locked`, no lost updates), the refresh-token race that
used to log users out, email uniqueness, and the `/api/health/` contract.
