"""
Django settings for shop_backend project.
"""

from pathlib import Path
from datetime import timedelta
import os

try:
    import dj_database_url
except ImportError:
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = bool(os.environ.get("VERCEL"))


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-local-development-only-change-me",
)

DEBUG = env_bool("DEBUG", default=not IS_VERCEL)

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "*,localhost,127.0.0.1,.vercel.app",
)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost,http://127.0.0.1,http://localhost:5173,http://localhost:5174,https://*.vercel.app",
)

CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

CLOUDINARY_ENABLED = all(
    [
        CLOUDINARY_CLOUD_NAME,
        CLOUDINARY_API_KEY,
        CLOUDINARY_API_SECRET,
    ]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_yasg",
    "django_filters",
    "accounts",
    "products",
    "sales",
]

if CLOUDINARY_ENABLED:
    try:
        import cloudinary
        import cloudinary_storage

        INSTALLED_APPS.insert(
            INSTALLED_APPS.index("django.contrib.staticfiles"),
            "cloudinary_storage",
        )
        INSTALLED_APPS.append("cloudinary")
    except ImportError:
        CLOUDINARY_ENABLED = False

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = "shop_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "shop_backend.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # Never fall back to SQLite when DATABASE_URL is set: silently degrading
    # to a per-instance /tmp database loses all data, so fail loudly instead.
    if dj_database_url is None:
        raise RuntimeError(
            "DATABASE_URL is set but dj-database-url is not installed. "
            "Add 'dj-database-url' to requirements.txt."
        )
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # SQLite fallback. WAL + busy_timeout + IMMEDIATE transactions keep
    # concurrent writes (sell / add-stock / return) from raising
    # "OperationalError: database is locked" (HTTP 500) and losing updates.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "/tmp/db.sqlite3" if IS_VERCEL else BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": 30,
                "transaction_mode": "IMMEDIATE",
                "init_command": (
                    "PRAGMA journal_mode=WAL;"
                    "PRAGMA synchronous=NORMAL;"
                    "PRAGMA busy_timeout=30000;"
                ),
            },
        }
    }

# Ephemeral storage warning: on Vercel, when DATABASE_URL is not configured the
# app falls back to SQLite inside /tmp, which is per-instance and gets wiped.
# Proven on production: parallel requests are served by different instances,
# so a just-created user returns 401/404 on most of them.
if IS_VERCEL and not DATABASE_URL:
    import sys

    print(
        "\n[CRITICAL] DATABASE_URL is not set on Vercel: falling back to "
        "ephemeral SQLite in /tmp. Data is lost when instances restart.\n",
        file=sys.stderr,
    )

AUTH_USER_MODEL = "accounts.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Dushanbe"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path("/tmp/media") if IS_VERCEL else BASE_DIR / "media"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# Do not use ManifestStaticFilesStorage here. Swagger/Redoc may be rendered
# inside a serverless function before a local manifest is available.
STATICFILES_BACKEND = "whitenoise.storage.CompressedStaticFilesStorage"

if CLOUDINARY_ENABLED:
    CLOUDINARY_STORAGE = {
        "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
        "API_KEY": CLOUDINARY_API_KEY,
        "API_SECRET": CLOUDINARY_API_SECRET,
    }
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": STATICFILES_BACKEND,
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": STATICFILES_BACKEND,
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Введите: Bearer <ваш_access_token>",
        }
    },
    "USE_SESSION_AUTH": False,
    "PERSIST_AUTH": True,
}

MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]

DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_IMAGE_SIZE_MB * 1024 * 1024 * 2
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_IMAGE_SIZE_MB * 1024 * 1024 * 2
