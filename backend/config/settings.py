"""Django settings. Everything environment-specific comes from env vars."""

import os
from pathlib import Path

import dj_database_url
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "customers",
    "orders",
    "segments",
    "flows",
    "messaging",
    "referrals",
    "reviews",
    "compliance",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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

# Postgres in docker compose via DATABASE_URL; SQLite fallback for local dev and tests.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=60
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "COERCE_DECIMAL_TO_STRING": False,
    # Unauthenticated for the local demo; production would verify provider signatures.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

# Integrations
USE_MOCKS = env_bool("USE_MOCKS", True)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SECONDS = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "5"))
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "10"))
MAILTRAP_API_TOKEN = os.environ.get("MAILTRAP_API_TOKEN", "")
MAILTRAP_SENDER_EMAIL = os.environ.get("MAILTRAP_SENDER_EMAIL", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

# Messaging copy
STORE_NAME = os.environ.get("STORE_NAME", "Swift Basket")
REVIEW_FORM_URL = os.environ.get("REVIEW_FORM_URL", "https://swiftbasket.example.com/review")
PUBLIC_REVIEW_URL = os.environ.get(
    "PUBLIC_REVIEW_URL", "https://reviews.example.com/swift-basket/write"
)
SMS_MAX_CHARS = 300
EMAIL_MAX_CHARS = 1000
SMS_OPT_OUT_FOOTER = "Reply STOP to opt out."
# Discount values are configuration, injected into copy; the model never chooses them.
DISCOUNTS = {
    "welcome_nudge": 10,
    "winback_offer": 10,
    "winback_final": 20,
    "referral_referee": 15,
    "referral_referrer": 15,
}

# Dashboard: a win-back enrollee counts as reactivated if they order within this window
REACTIVATION_WINDOW_DAYS = int(os.environ.get("REACTIVATION_WINDOW_DAYS", "14"))

# Compliance: every send passes the gate in compliance/gate.py
QUIET_HOURS_START = int(os.environ.get("QUIET_HOURS_START", "21"))
QUIET_HOURS_END = int(os.environ.get("QUIET_HOURS_END", "8"))
WEEKLY_MESSAGE_CAP = int(os.environ.get("WEEKLY_MESSAGE_CAP", "3"))
DEFAULT_CUSTOMER_TIMEZONE = os.environ.get("DEFAULT_CUSTOMER_TIMEZONE", "America/New_York")

# Celery (worker + beat)
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BEAT_SCHEDULE = {
    "process-due-enrollments": {
        "task": "flows.tasks.process_due_enrollments_task",
        "schedule": 60.0,
    },
    "dispatch-deferred-messages": {
        "task": "compliance.tasks.dispatch_deferred_task",
        "schedule": 300.0,
    },
    "daily-segments-and-winback": {
        "task": "flows.tasks.daily_refresh_task",
        "schedule": crontab(hour=14, minute=0),  # 10:00 US Eastern, inside send hours
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
