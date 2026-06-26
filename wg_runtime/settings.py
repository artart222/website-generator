from __future__ import annotations

import os
import sys
from pathlib import Path

from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Detect a test run so secure production defaults don't block the test runner.
_UNDER_TEST = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ


def _env_flag(name: str, default: str = "False") -> bool:
    return os.environ.get(name, default).lower() in {"1", "true", "yes"}


def _env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# Secure by default: production must opt OUT via explicit env vars. Under tests
# we default to DEBUG so a dev key/host config is used without external setup.
DEBUG = _env_flag("DJANGO_DEBUG", "True" if _UNDER_TEST else "False")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-insecure-key-not-for-production"
    else:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is not enabled."
        )

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Where the runtime reads its integrations provider map from (no SSG import).
WG_CONFIG_PATH = os.environ.get("WG_CONFIG_PATH", str(PROJECT_ROOT / "config.yaml"))

# CORS: explicit allow-list (only used when DEBUG is False; DEBUG allows all).
WG_CORS_ALLOWED_ORIGINS = _env_list("WG_CORS_ALLOWED_ORIGINS")

# Payment callback signing (opt-in; strongly recommended in production).
WG_REQUIRE_SIGNED_CALLBACKS = _env_flag("WG_REQUIRE_SIGNED_CALLBACKS", "False")
WG_PAYMENT_CALLBACK_SECRET = os.environ.get("WG_PAYMENT_CALLBACK_SECRET", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "wg_runtime.runtime",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "wg_runtime.middleware.CORSMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wg_runtime.urls"

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
    }
]

WSGI_APPLICATION = "wg_runtime.wsgi.application"
ASGI_APPLICATION = "wg_runtime.asgi.application"

DATABASE_ENGINE = os.environ.get("RUNTIME_DATABASE_ENGINE", "sqlite").lower()
DATABASE_NAME = os.environ.get("RUNTIME_DATABASE_NAME", str(BASE_DIR / "db.sqlite3"))
DATABASE_USER = os.environ.get("RUNTIME_DATABASE_USER", "")
DATABASE_PASSWORD = os.environ.get("RUNTIME_DATABASE_PASSWORD", "")
DATABASE_HOST = os.environ.get("RUNTIME_DATABASE_HOST", "")
DATABASE_PORT = os.environ.get("RUNTIME_DATABASE_PORT", "")

if DATABASE_ENGINE == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DATABASE_NAME,
            "USER": DATABASE_USER,
            "PASSWORD": DATABASE_PASSWORD,
            "HOST": DATABASE_HOST,
            "PORT": DATABASE_PORT,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATABASE_NAME,
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
MEDIA_URL = os.environ.get("RUNTIME_MEDIA_URL", "/media/")
MEDIA_ROOT = os.environ.get("RUNTIME_MEDIA_ROOT", str(BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# JWT: staff obtain tokens via POST /token/obtain/ (username + password).
# Storefront endpoints explicitly use AllowAny; admin routes require staff JWT.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5 if _UNDER_TEST else 60),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=1 if _UNDER_TEST else 24),
    "ROTATE_REFRESH_TOKENS": False,
    "SIGNING_KEY": SECRET_KEY,
}

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = _env_flag(
    "CELERY_TASK_ALWAYS_EAGER", "True" if _UNDER_TEST else "False"
)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "retry-due-outbox-events": {
        "task": "wg_runtime.runtime.integrations.tasks.retry_due_outbox_events",
        "schedule": 60.0,
        "args": (100,),
    }
}
