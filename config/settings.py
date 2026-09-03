from pathlib import Path
from decouple import config
import os
from datetime import timedelta
from django.urls import reverse_lazy

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
    "django.middleware.gzip.GZipMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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


# Static files (CSS, JavaScript, Images) with WhiteNoise compression & caching
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

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
CELERY_RESULT_EXPIRES = 3600  # 1 hour auto-prune for Redis task cache


# DRF, JWT & Rate Limiting (Throttling) Configuration
# ==============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/minute",
        "user": "600/minute",
        "otp": "5/minute",
        "auth": "30/minute",
        "ai_generation": "15/minute",
    },
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
    "http://localhost:3001,http://127.0.0.1:3001,"
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

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    "ngrok-skip-browser-warning",
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
    "http://localhost:3001,http://127.0.0.1:3001,"
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "https://*.ngrok-free.app,https://*.ngrok-free.dev,https://*.ngrok.app,https://*.ngrok.dev,https://*.ngrok.io,https://*.loca.lt,"
    "http://*.ngrok-free.app,http://*.ngrok-free.dev,http://*.ngrok.app,http://*.ngrok.dev,http://*.ngrok.io,http://*.loca.lt"
)
_csrf_origins_env = config("CSRF_TRUSTED_ORIGINS", default=_default_csrf_origins)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in _csrf_origins_env.split(",") if origin.strip()
]


# Django Unfold Admin Configuration
# ==============================================================================
UNFOLD = {
    "SITE_TITLE": "BANCre Admin Console",
    "SITE_HEADER": "BANCre Management Console",
    "SITE_URL": "/",
    "SITE_SYMBOL": "real_estate_agent",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "238 242 255",
            "100": "224 231 255",
            "200": "199 210 254",
            "300": "165 180 252",
            "400": "129 140 248",
            "500": "99 102 241",
            "600": "79 70 229",
            "700": "67 56 202",
            "800": "55 48 163",
            "900": "49 46 129",
            "950": "30 27 75",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Authentication & Security",
                "separator": True,
                "items": [
                    {
                        "title": "User Accounts",
                        "icon": "group",
                        "link": reverse_lazy("admin:accounts_customuser_changelist"),
                    },
                    {
                        "title": "System Roles",
                        "icon": "badge",
                        "link": reverse_lazy("admin:accounts_rolemodel_changelist"),
                    },
                    {
                        "title": "Media Files",
                        "icon": "perm_media",
                        "link": reverse_lazy("admin:accounts_mediafile_changelist"),
                    },
                    {
                        "title": "OTP Verification Logs",
                        "icon": "pin",
                        "link": reverse_lazy("admin:accounts_otp_changelist"),
                    },
                ],
            },
            {
                "title": "Real Estate Assets",
                "separator": True,
                "items": [
                    {
                        "title": "Properties",
                        "icon": "apartment",
                        "link": reverse_lazy("admin:properties_property_changelist"),
                    },
                    {
                        "title": "Property Documents",
                        "icon": "folder",
                        "link": reverse_lazy("admin:properties_propertyfile_changelist"),
                    },
                ],
            },
            {
                "title": "Commercial Financing",
                "separator": True,
                "items": [
                    {
                        "title": "Loan Requests",
                        "icon": "request_quote",
                        "link": reverse_lazy("admin:loan_loanrequest_changelist"),
                    },
                    {
                        "title": "Loan Quotes",
                        "icon": "payments",
                        "link": reverse_lazy("admin:loan_loanquote_changelist"),
                    },
                ],
            },
            {
                "title": "AI Offering Memorandums",
                "separator": True,
                "items": [
                    {
                        "title": "Memorandums",
                        "icon": "description",
                        "link": reverse_lazy("admin:memorandums_memorandum_changelist"),
                    },
                    {
                        "title": "Memorandum Sections",
                        "icon": "view_list",
                        "link": reverse_lazy("admin:memorandums_memorandumsection_changelist"),
                    },
                ],
            },
            {
                "title": "AI Assistant",
                "separator": True,
                "items": [
                    {
                        "title": "Conversations",
                        "icon": "forum",
                        "link": reverse_lazy("admin:chatbot_conversation_changelist"),
                    },
                    {
                        "title": "Messages",
                        "icon": "chat",
                        "link": reverse_lazy("admin:chatbot_message_changelist"),
                    },
                ],
            },
            {
                "title": "System Alerts & Tasks",
                "separator": True,
                "items": [
                    {
                        "title": "Notifications",
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                    {
                        "title": "Email Preferences",
                        "icon": "tune",
                        "link": reverse_lazy("admin:notifications_notificationpreference_changelist"),
                    },
                    {
                        "title": "Celery Tasks",
                        "icon": "task_alt",
                        "link": reverse_lazy("admin:django_celery_results_taskresult_changelist"),
                    },
                ],
            },
        ],
    },
}

