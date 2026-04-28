"""Test settings — fast in-memory SQLite, no external services.

Run the suite with::

    DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test apps.mentor

This file is independent of ``development.py`` so dev tweaks don't leak into
test runs.
"""

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-only-not-a-secret"  # noqa: S105

# In-memory SQLite: zero setup, fast, isolates tests from the Postgres dev DB.
# Both ``default`` and ``sandbox`` aliases point at the same in-memory store
# because ``SandboxDatabaseRouter.allow_migrate`` already keeps app models off
# the sandbox alias — but the alias must still exist so the router has
# something to refuse.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    "sandbox": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# MD5 is fine for tests and ~10x faster than the default PBKDF2 hasher.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# AI Mentor: tests never call the real SDK, but settings need a value.
GEMINI_API_KEY = "test-key-not-used"
AI_MENTOR_MODEL = "gemini-flash-latest"
