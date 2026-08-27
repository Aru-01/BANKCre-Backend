from pathlib import Path
from decouple import config
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-_7zs08^juy8+j92*2c)x+y!@5fe(z&cr!-hnx*@%3ab68v@_41",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)
AUTH_USER_MODEL = "accounts.CustomUser"

_allowed_hosts_env = config("ALLOWED_HOSTS", default="*")
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(",") if host.strip()]
if "*" in ALLOWED_HOSTS or DEBUG:
    default_dev_hosts = [
        "testserver",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        ".ngrok-free.app",
        ".ngrok-free.dev",
        ".ngrok.app",
        ".ngrok.dev",
        ".ngrok.io",
        ".loca.lt",
    ]
    for h in default_dev_hosts:
        if h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Application definition

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# Third-Party Apps
INSTALLED_APPS += [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "debug_toolbar",
    "corsheaders",
    "drf_yasg",
    "django_celery_results",
]

# Custom Apps
INSTALLED_APPS += [
    "accounts",
    "properties",
    "memorandums",
    "chatbot",
    "loan",
    "notifications",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
INTERNAL_IPS = [
    "127.0.0.1",
]
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database Configuration (PostgreSQL with SQLite fallback)
# =========================
DB_NAME = config("DB_NAME", default="")
DB_USER = config("DB_USER", default="")
DB_PASSWORD = config("DB_PASSWORD", default="")
DB_HOST = config("DB_HOST", default="localhost")
DB_PORT = config("DB_PORT", default="5432")
DB_ENGINE = config("DB_ENGINE", default="django.db.backends.postgresql")

if DB_NAME:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Allow large file uploads (50 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB
FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]


# AI API Keys
# =========================
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
CLAUDE_API_KEY = config("CLAUDE_API_KEY", default="")


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = f"BANCre <{EMAIL_HOST_USER}>"

COMPANY_LOGO_URL = config(
    "COMPANY_LOGO_URL", default="https://i.ibb.co.com/dw1P2S9K/BANCre.webp"
)

# Celery Configuration Options
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE


# DRF & JWT Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}


# CORS Configuration
# =========================
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=False, cast=bool)

# Specific allowed origins (loaded from .env as comma-separated strings)
_default_cors_origins = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8000,http://127.0.0.1:8000"
)
_cors_origins_env = config("CORS_ALLOWED_ORIGINS", default=_default_cors_origins)
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()
]

# Regex pattern support for dynamic domains (e.g. ngrok, localtunnel, preview environments)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?:\/\/.*\.ngrok-free\.app$",
    r"^https?:\/\/.*\.ngrok-free\.dev$",
    r"^https?:\/\/.*\.ngrok\.app$",
    r"^https?:\/\/.*\.ngrok\.dev$",
    r"^https?:\/\/.*\.ngrok\.io$",
    r"^https?:\/\/.*\.loca\.lt$",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]


# CSRF Trusted Origins (needed for POST/PATCH across domains, ngrok, and frontend apps)
# =========================
_default_csrf_origins = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "https://*.ngrok-free.app,https://*.ngrok-free.dev,https://*.ngrok.app,https://*.ngrok.dev,https://*.ngrok.io,https://*.loca.lt,"
    "http://*.ngrok-free.app,http://*.ngrok-free.dev,http://*.ngrok.app,http://*.ngrok.dev,http://*.ngrok.io,http://*.loca.lt"
)
_csrf_origins_env = config("CSRF_TRUSTED_ORIGINS", default=_default_csrf_origins)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in _csrf_origins_env.split(",") if origin.strip()
]

