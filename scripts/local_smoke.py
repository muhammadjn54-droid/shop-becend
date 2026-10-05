"""Run a disposable local API for UI checks. Never opens the real database."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DJANGO_SETTINGS_MODULE"] = "shop_backend.test_settings"
os.environ.pop("TEST_DATABASE_URL", None)

import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connections

with tempfile.TemporaryDirectory(prefix="shop-ui-check-") as directory:
    settings.DATABASES["default"]["NAME"] = str(Path(directory) / "test.sqlite3")
    settings.MEDIA_ROOT = str(Path(directory) / "media")
    settings.STORAGES["default"] = {"BACKEND": "django.core.files.storage.FileSystemStorage"}
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5175", "http://127.0.0.1:5175"]
    call_command("migrate", interactive=False, verbosity=0)
    get_user_model().objects.create_user(username="ui-check", password="Temporary-UI-Check123!", first_name="Проверка", email="ui-check@example.test")
    print("Disposable UI account: ui-check / Temporary-UI-Check123!", flush=True)
    port = os.environ.get("UI_SMOKE_PORT", "8000")
    try:
        call_command("runserver", f"127.0.0.1:{port}", use_reloader=False)
    finally:
        connections.close_all()
