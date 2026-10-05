"""Isolated checks: never use a developer's database, email or cloud storage."""
import atexit
import os
from tempfile import TemporaryDirectory

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
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
_test_media_directory = TemporaryDirectory(prefix="shop-test-media-")
atexit.register(_test_media_directory.cleanup)
MEDIA_ROOT = Path(_test_media_directory.name)  # noqa: F405
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
