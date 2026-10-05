"""Isolated checks: never use a developer's database, email or cloud storage."""
import os

os.environ.update(
    LOAD_DOTENV="false",
    DEBUG="True", PRODUCTION="False", VERCEL="", RENDER="", DATABASE_URL="",
    DATA_DIR="", CLOUDINARY_CLOUD_NAME="", CLOUDINARY_API_KEY="", CLOUDINARY_API_SECRET="",
    SECRET_KEY="isolated-test-secret-never-use-in-production-12345678901234567890",
    ALLOWED_HOSTS="localhost,127.0.0.1,testserver",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)

from .settings import *  # noqa: F403,E402

DATABASES["default"]["NAME"] = ":memory:"  # noqa: F405
if os.environ.get("TEST_DATABASE_URL"):
    import dj_database_url
    DATABASES["default"] = dj_database_url.parse(os.environ["TEST_DATABASE_URL"], conn_max_age=0)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
