from .base import *  # noqa: F401, F403

DEBUG = True

# In development, Django serves with the dev server — no need for HTTPS cookies
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Console email backend for password reset during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
