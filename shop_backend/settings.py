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

# Load local .env if present
_env_file = BASE_DIR / ".env"
if _env_file.exists() and os.environ.get("LOAD_DOTENV", "true").lower() not in {"0", "false", "no"}:
    with open(_env_file, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            _k = _k.strip()
            _v = _v.strip().strip("'\"")
            if _k not in os.environ:
                os.environ[_k] = _v

IS_VERCEL = bool(os.environ.get("VERCEL"))
IS_RENDER = bool(os.environ.get("RENDER"))
# On Render the filesystem is ephemeral unless a Persistent Disk is mounted at
# /var/data. Pointing DATA_DIR at the disk keeps SQLite and uploaded images
# across restarts and redeploys.
DATA_DIR = os.environ.get("DATA_DIR") or ""


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


IS_PRODUCTION = IS_VERCEL or IS_RENDER or env_bool("PRODUCTION")

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-local-development-only-change-me",
)

DEBUG = env_bool("DEBUG", default=not IS_PRODUCTION)
if (IS_PRODUCTION or not DEBUG) and (
    len(SECRET_KEY) < 50
    or SECRET_KEY.startswith(("django-insecure-", "change-me"))
):
    raise RuntimeError("Set SECRET_KEY to a stable random secret of at least 50 characters.")

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,.vercel.app,.onrender.com",
)
render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost,http://127.0.0.1,http://localhost:5173,http://localhost:5174,https://*.vercel.app,https://*.onrender.com",
)
render_url = os.environ.get("RENDER_EXTERNAL_URL")
if render_url and render_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(render_url)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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
    except ImportError as exc:
        raise RuntimeError("Cloudinary is configured but its storage dependencies are missing.") from exc

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

cors_origins = env_list("CORS_ALLOWED_ORIGINS", "")
if cors_origins:
    CORS_ALLOWED_ORIGINS = cors_origins
    CORS_ALLOW_ALL_ORIGINS = False
else:
    CORS_ALLOW_ALL_ORIGINS = DEBUG and not IS_PRODUCTION
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
    if IS_VERCEL:
        raise RuntimeError("Vercel requires a persistent PostgreSQL DATABASE_URL; /tmp SQLite loses accounts.")
    if IS_PRODUCTION and not DATA_DIR:
        raise RuntimeError("Production requires DATABASE_URL or DATA_DIR on a mounted persistent disk.")
    if DATA_DIR:
        if not Path(DATA_DIR).is_absolute():
            raise RuntimeError("DATA_DIR must be an absolute path on a persistent disk.")
        SQLITE_PATH = str(Path(DATA_DIR) / "db.sqlite3")
        Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    else:
        SQLITE_PATH = str(BASE_DIR / "db.sqlite3")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_PATH,
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

if IS_PRODUCTION and DATABASE_URL and "sqlite" in DATABASES["default"]["ENGINE"]:
    raise RuntimeError("Do not use a SQLite DATABASE_URL in production; use PostgreSQL or persistent DATA_DIR.")
if IS_VERCEL and "postgresql" not in DATABASES["default"]["ENGINE"]:
    raise RuntimeError("Vercel requires a shared PostgreSQL DATABASE_URL.")
if IS_PRODUCTION and not CLOUDINARY_ENABLED and (IS_VERCEL or not DATA_DIR):
    raise RuntimeError("Production uploads require Cloudinary or DATA_DIR on a persistent disk.")

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
if IS_VERCEL:
    MEDIA_ROOT = Path("/tmp/media")
elif DATA_DIR:
    MEDIA_ROOT = Path(DATA_DIR) / "media"
else:
    MEDIA_ROOT = BASE_DIR / "media"
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
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    # Stable refresh tokens avoid simultaneous-tab rotation races and let
    # logout revoke the actual token used by every tab in that session.
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "CHECK_REVOKE_TOKEN": True,
    "UPDATE_LAST_LOGIN": True,
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

# Email settings for password reset and notifications
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST_USER
    else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or "Shop Inventory <noreply@shop-inventory.local>",
)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
