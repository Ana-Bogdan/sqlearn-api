# sqlearn-api

Backend for SQLearn, a gamified SQL learning platform. It serves the curriculum
(chapters, lessons, exercises, hints), runs learner-submitted SQL inside
isolated per-user PostgreSQL schemas, tracks progress and gamification
(XP, badges, leaderboard), handles cookie-based JWT authentication, and exposes
an AI mentor backed by the Google Gemini API.

Built with Django 5.1 and Django REST Framework. Authentication uses
djangorestframework-simplejwt with the tokens carried in httpOnly cookies.
Data lives in PostgreSQL; user SQL is executed through a separate database
connection (`sandbox` alias) routed by `apps.sandbox.routers.SandboxDatabaseRouter`.

## Prerequisites

- Python 3.12 and PostgreSQL 16, or
- Docker with Docker Compose (runs both the API and the database)
- A Google Gemini API key for the AI mentor (the rest of the app works without it;
  mentor endpoints return a fallback message when the key is missing)

## Setup with Docker Compose

This is the path the project is configured for. The database host defaults to
`db`, the service name in `docker-compose.yml`.

1. Create the env file from the template and fill in your Gemini key:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `GEMINI_API_KEY` (leave it empty to run without the mentor).

2. Build and start the stack. The `api` service runs migrations automatically on
   start, then launches the dev server:

   ```bash
   docker compose up --build
   ```

3. Seed the curriculum and the sandbox playground (run in a separate terminal):

   ```bash
   docker compose exec api python manage.py seed_curriculum
   docker compose exec api python manage.py seed_playground
   ```

The API is now on http://localhost:8000 and PostgreSQL on port 5432.

## Setup without Docker

Use this if you run PostgreSQL yourself. Point the database host at `localhost`
instead of the compose default `db`.

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a PostgreSQL database and user matching the defaults
   (`sqlearn` / `sqlearn`, database `sqlearn`), or adjust the env vars below.

3. Create `.env` from the template and override the database host:

   ```bash
   cp .env.example .env
   ```

   In `.env`, set `DATABASE_URL=postgres://sqlearn:sqlearn@localhost:5432/sqlearn`
   and add `POSTGRES_HOST=localhost`. Settings read the individual
   `POSTGRES_*` variables; `POSTGRES_HOST` defaults to `db`, so it must be set to
   `localhost` for a local database.

4. Run migrations, seed, and start the server:

   ```bash
   python manage.py migrate
   python manage.py seed_curriculum
   python manage.py seed_playground
   python manage.py runserver 0.0.0.0:8000
   ```

`manage.py` defaults to `config.settings.development`.

## Environment variables

From `.env.example`:

| Variable | Purpose |
| --- | --- |
| `DEBUG` | Django debug flag |
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | Postgres connection string (informational; settings read the `POSTGRES_*` vars) |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API (also used for CSRF trusted origins) |
| `GEMINI_API_KEY` | Google Gemini API key for the AI mentor |
| `AI_MENTOR_MODEL` | Gemini model name (default `gemini-flash-latest`) |
| `AI_MENTOR_RATE_LIMIT_PER_HOUR` | Mentor requests allowed per user per hour |
| `AI_MENTOR_HINTS_PER_EXERCISE` | Hint cap per exercise |
| `AI_MENTOR_TIMEOUT_SECONDS` | Per-request Gemini timeout |
| `AI_MENTOR_MAX_RETRIES` | Retries on transient Gemini errors |

The Docker Compose `api` service additionally sets `POSTGRES_HOST=db` and the
`POSTGRES_*` credentials. Optional `SANDBOX_DB_*` variables point user-SQL
execution at a restricted database role in production; they default to the main
credentials so local setups need no extra configuration.

## Useful commands

- Promote a seeded test user and exercise a full mentor flow:
  `bash scripts/verify_mentor.sh`
- Seed a user with a completed chapter (to test the chapter quiz):
  `docker compose exec api python manage.py seed_test_user`
- Run the test suite (in-memory SQLite, no external services):
  `DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test`
- Django admin: create a superuser with
  `python manage.py createsuperuser`, then visit http://localhost:8000/admin/

## How it connects to the frontend

The API listens on port 8000. The frontend (`sqlearn-web`) calls it at
`http://localhost:8000/api` by default and runs on http://localhost:3000.
`CORS_ALLOWED_ORIGINS` is set to `http://localhost:3000` so the browser can send
credentialed requests; JWTs are delivered as httpOnly cookies and the frontend
reads the `csrftoken` cookie to send it back as the `X-CSRFToken` header.

## Project structure

```
config/            Django project: settings (base/development/test), urls, wsgi/asgi
apps/
  authentication/  Cookie-based JWT auth, registration, password reset, CSRF
  users/           Custom user model and profile endpoints
  curriculum/      Chapters, lessons, exercises, hints (+ seed_curriculum)
  sandbox/         Per-user SQL execution, schema routing (+ seed_playground)
  progress/        Per-user exercise and lesson progress
  gamification/    XP, badges, leaderboard
  mentor/          AI mentor endpoints (hint, explain-error, nl-to-sql)
  admin_api/       Admin-only content and log management endpoints
  health/          Health check at /api/health/
manage.py
requirements.txt
docker-compose.yml
Dockerfile
```

All API routes are mounted under `/api/` (see `config/urls.py`).
