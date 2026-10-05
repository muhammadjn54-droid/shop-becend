# Shop Inventory API

Django REST API for accounts, products, stock, sales, returns and statistics.
For persistent production deployment, including PostgreSQL setup in Tajik, see [DEPLOY.md](DEPLOY.md).

## Local development (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Use registration to create a normal account. There is no seeded administrator or public default password.
Create an administrator only when needed with `python manage.py createsuperuser`.
Local development uses SQLite; production requires persistent storage. Never run production with test settings.

## Checks

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=shop_backend.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=shop_backend.test_settings
```

These settings isolate tests from your real database, uploads and outgoing email.
`python scripts/local_smoke.py` creates a disposable local server at port 8001 with a documented test-only account and removes its temporary data when stopped. It must never be deployed.

## API contracts

Swagger: `/swagger/`; Redoc: `/redoc/`; database health: `/api/health/`.

- `POST /api/auth/register/`, `/login/`: return access, refresh and user.
- `POST /api/auth/token/refresh/`: stable refresh token, returns a new access token.
- `GET/PATCH /api/auth/me/`: profile, editable username/first_name/last_name. Email is read-only.
- `POST /api/auth/logout/`: revoke the supplied refresh token even if access expired.
- `POST /api/auth/forgot-password/`, `/reset-password/`: email reset flow; SMTP required in production.
- `GET/POST /api/products/`, `GET/PATCH/PUT/DELETE /api/products/{id}/`.
- `POST /api/products/{id}/sell/`, `/add-stock/`, `/return/`.
- `GET /api/products/{id}/sales/`, `/api/products/low-stock/`.
- `GET /api/sales/`, `/api/sales/{id}/`, `/api/statistics/`, `/api/dashboard/`.

Lists use pages of 20. Product, low-stock and sales lists accept `search` (name or barcode).
Every object is scoped to the authenticated owner. Logout revokes refresh; already issued access tokens expire within 15 minutes. Password reset invalidates both types.

## Stock and history

Sales snapshot the purchase and selling prices. Returns reduce revenue, cost, profit and loss using those historical prices. Changing current prices never rewrites sale history.
Sell, return and stock changes use database transactions and lock the product row. Edits reload the row before applying writable fields; clients should send `expected_updated_at` from their last product read to reject stale edits.

DELETE archives the product: it disappears from active stock but keeps sales and returns. An archived product cannot be edited, sold or restocked, but a previous sale can be returned. Archived units are reported separately from active remaining stock. Database foreign keys protect sale history from hard deletion. The admin ledger is read-only; create sales and returns through the API.

Images accept JPEG/PNG/WebP up to 5 MB per file. Remote URLs are not downloaded. Galleries validate before writing and failed uploads roll back the product change. Configure Cloudinary on Vercel; its filesystem cannot retain uploads.

## Existing installations

Back up the database and uploads before migrations. Migration 0005 rejects ambiguous case-insensitive usernames/emails with affected IDs; resolve those records with their owners before retrying. It never silently merges accounts.

The former default-admin migration is now a no-op. Existing installations that already ran it retain their accounts: audit those administrators and use `python manage.py changepassword <username>` to replace any old default password. New password-bound JWT checks may require existing users to log in once after this release.
