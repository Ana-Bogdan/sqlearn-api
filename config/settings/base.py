import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local
    "apps.users",
    "apps.health",
    "apps.authentication",
    "apps.curriculum",
    "apps.sandbox",
    "apps.progress",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "sqlearn"),
        "USER": os.getenv("POSTGRES_USER", "sqlearn"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "sqlearn"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    },
    # Separate connection used exclusively for executing user SQL in per-user
    # schemas. Defaults to the same credentials so local dev works without
    # extra setup; production should point this at the restricted
    # ``sqlearn_sandbox`` role that has no access to app tables.
    "sandbox": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("SANDBOX_DB_NAME", os.getenv("POSTGRES_DB", "sqlearn")),
        "USER": os.getenv("SANDBOX_DB_USER", os.getenv("POSTGRES_USER", "sqlearn")),
        "PASSWORD": os.getenv(
            "SANDBOX_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "sqlearn")
        ),
        "HOST": os.getenv("SANDBOX_DB_HOST", os.getenv("POSTGRES_HOST", "db")),
        "PORT": os.getenv("SANDBOX_DB_PORT", os.getenv("POSTGRES_PORT", "5432")),
    },
}

DATABASE_ROUTERS = ["apps.sandbox.routers.SandboxDatabaseRouter"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "apps.authentication.validators.ComplexityValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.authentication.authentication.CookieJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

# JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Auth cookies (httpOnly transport for JWTs)
AUTH_COOKIE_ACCESS = "access_token"
AUTH_COOKIE_REFRESH = "refresh_token"
AUTH_COOKIE_SAMESITE = "Lax"
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "False").lower() == "true"
AUTH_COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN") or None
AUTH_COOKIE_PATH = "/"

# CORS
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
CORS_ALLOW_CREDENTIALS = True

# CSRF
CSRF_TRUSTED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
CSRF_COOKIE_HTTPONLY = False  # Frontend reads csrftoken cookie to send X-CSRFToken header
CSRF_COOKIE_SAMESITE = "Lax"

# Password reset
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24  # 24 hours
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@sqlearn.local")
PASSWORD_RESET_URL_TEMPLATE = os.getenv(
    "PASSWORD_RESET_URL_TEMPLATE",
    "http://localhost:3000/reset-password/{uid}/{token}",
)
