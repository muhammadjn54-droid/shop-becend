# Shop Inventory API

Django REST Framework backend for products, stock, sales, returns and shop statistics.

## Main endpoints

- `POST /api/auth/login/`
- `POST /api/auth/token/refresh/`
- `GET /api/auth/me/`
- `POST /api/auth/logout/`
- `GET/POST /api/products/`
- `GET/PATCH/PUT/DELETE /api/products/{id}/`
- `POST /api/products/{id}/sell/`
- `POST /api/products/{id}/add-stock/`
- `POST /api/products/{id}/return/`
- `GET /api/products/{id}/sales/`
- `GET /api/products/low-stock/`
- `GET /api/sales/`
- `GET /api/sales/{id}/`
- `GET /api/statistics/`
- `GET /api/dashboard/`

Swagger is available at `/`, `/swagger/` and Redoc at `/redoc/`.

## Accounting logic

Each sale stores a financial snapshot at the moment of sale:

- `price_per_item` — actual sale price
- `purchase_price_per_item` — purchase price at that moment
- `total_amount = quantity * price_per_item`
- `cost_amount = quantity * purchase_price_per_item`
- `profit` and `loss` are stored on the sale

Product revenue, cost, profit and loss are calculated from real sales and reduced by real returns. Changing the current product price later does not rewrite old sale history.

Returns are stored in `SaleReturn`. `POST /api/products/{id}/return/` accepts:

```json
{
  "quantity": 1
}
```

Optional `sale_id` can be supplied. Without it, returns are applied to the newest available sales first (LIFO).

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Production environment

Never commit real secrets. Configure them in Vercel Environment Variables.

Recommended variables:

```env
SECRET_KEY=strong-random-secret
DEBUG=False
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
ALLOWED_HOSTS=shop-becend.vercel.app,.vercel.app
CORS_ALLOWED_ORIGINS=https://YOUR-FRONTEND.vercel.app
CSRF_TRUSTED_ORIGINS=https://shop-becend.vercel.app/
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

### PostgreSQL

If `DATABASE_URL` is set, the project uses PostgreSQL through `dj-database-url`. Local development falls back to SQLite.

Vercel also has a SQLite fallback only so the deployment can boot before configuration, but `/tmp` is not persistent and must not be used for real production data. Set `DATABASE_URL` before using the application with real data.

### Product images

If all three Cloudinary variables are configured, uploaded product images use Cloudinary storage.

Without them, local filesystem storage is used. Vercel filesystem is not persistent, so Cloudinary or another persistent object storage should be configured in production.

## Deploy / migration

After changing models:

```bash
python manage.py migrate
python manage.py check
python manage.py test
```

The migration `sales/0002_sale_snapshots_and_returns.py` backfills old sales using the already stored financial values:

```
cost_amount = total_amount - profit + loss
```

This preserves old accounting as accurately as the existing data allows.

## JWT

Send protected requests with:

```http
Authorization: Bearer <access_token>
```

Every product and sale query is scoped to `request.user`.

