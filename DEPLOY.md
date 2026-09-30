# Production deployment (Vercel)

Backend: Django + DRF, deployed to `https://shop-becend.vercel.app`.

## Why environment variables are required

Vercel runs each request in a **separate serverless instance** with its own
writable `/tmp`. Anything stored in `/tmp` is not shared between instances and
is deleted when an instance is recycled.

Measured on production: one freshly registered user, one valid token, 10
parallel requests:

```
8x  HTTP 401  (user not found on this instance)
2x  HTTP 200  (user found)
```

Without a shared database the app therefore loses accounts, products and sales,
and returns 401/404/500 at random. `shop_backend/settings.py` prints a
`[CRITICAL]` warning on boot while this is unconfigured.

## 1. Create a PostgreSQL database

Any hosted Postgres works. Free options: Vercel Postgres, Neon, Supabase.

Copy the **pooled** connection string, e.g.

```
postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

## 2. Add the environment variable

Vercel dashboard → *shop-becend* → **Settings → Environment Variables** →
add for **Production** (and **Preview**):

| Name          | Value                        |
| ------------- | ---------------------------- |
| `DATABASE_URL` | the pooled Postgres URL     |

Set it for **both** Production and Preview, otherwise preview deployments keep
writing to `/tmp`.

## 3. Run the migrations once

Vercel does not run migrations on deploy, so do it manually to avoid a
build-time race between instances:

```bash
npx vercel env pull .env.production.local --environment=production
# then, with DATABASE_URL exported from that file:
python manage.py migrate
```

## 4. Verify

```bash
# schema is live
curl https://shop-becend.vercel.app/swagger/?format=openapi | grep barcode

# a user now survives parallel requests
# (before the fix, ~8/10 returned 401)
```

Set the same variable locally in `.env` to develop against the same database.

## Product images (also ephemeral)

Without Cloudinary, `MEDIA_ROOT` is `/tmp/media`, so uploaded images disappear
when an instance recycles. The code already supports Cloudinary — it is
enabled automatically when all three variables are present:

| Name                    | Value            |
| ----------------------- | ---------------- |
| `CLOUDINARY_CLOUD_NAME` | from Cloudinary  |
| `CLOUDINARY_API_KEY`    | from Cloudinary  |
| `CLOUDINARY_API_SECRET` | from Cloudinary  |

Once they are set, new uploads are stored in Cloudinary and served from a CDN.
Images uploaded before this change are already lost and cannot be recovered.

## Related commits

- `5a075c6` — fix `HTTP 500 database is locked` under concurrent writes
- `4c96cdf` — fail loudly instead of silently falling back to `/tmp` SQLite
