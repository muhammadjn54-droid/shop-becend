"""
WSGI config for shop_backend project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shop_backend.settings")

application = get_wsgi_application()
app = application

# Temporary compatibility for the current Vercel deployment:
# when no persistent DATABASE_URL exists, /tmp SQLite starts empty on a cold
# instance, so migrations must be applied before requests can use the API.
# This can be disabled after a persistent PostgreSQL database is configured by
# setting VERCEL_AUTO_MIGRATE=False.
if os.environ.get("VERCEL") and os.environ.get("VERCEL_AUTO_MIGRATE", "True").lower() in {
    "1",
    "true",
    "yes",
    "on",
}:
    try:
        from django.core.management import call_command

        call_command("migrate", interactive=False, verbosity=0)
    except Exception as exc:
        print("Vercel auto-migrate error:", exc)
