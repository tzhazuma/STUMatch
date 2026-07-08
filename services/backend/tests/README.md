# UniMatch Backend Tests

This directory contains pytest integration tests for the UniMatch FastAPI backend. The tests run against real PostgreSQL (with pgvector) and Redis services started via Docker Compose.

## Prerequisites

- Python 3.12+ (other versions may work but are not tested)
- Docker Compose (to run PostgreSQL, Redis, and MinIO)
- A virtual environment with dependencies from `requirements.txt`

## Starting the Docker services

From the project root:

```bash
docker compose -f infra/docker-compose.yml up -d
```

This starts:

- PostgreSQL with pgvector on `localhost:5432`
- Redis on `localhost:6379`
- MinIO on `localhost:9000` / `localhost:9001`

## Creating the test database

The tests use a separate database named `unimatch_test`. Create it once:

```bash
docker exec unimatch-postgres psql -U unimatch -d postgres -c "CREATE DATABASE unimatch_test;"
```

## Installing Python dependencies

```bash
cd services/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Note:** `requirements.txt` pins `bcrypt==3.2.2` because `passlib==1.7.4` is incompatible with newer bcrypt versions (4.0+), which reject the long passwords used during passlib's bcrypt backend detection.

## Running the tests

```bash
cd services/backend
source .venv/bin/activate
pytest
```

To see verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/test_auth.py -v
```

## What is covered

- `POST /auth/send-verification-code` — mock email provider stores the code in Redis.
- `POST /auth/register` — registration with a valid email verification code.
- `POST /auth/login` — login with correct credentials and failure with wrong password.
- `GET /users/me` — fetch current user with JWT.
- `PUT /users/me` — update the current user's email.
- `GET /profiles/me` — fetch current profile with JWT.
- `PUT /profiles/me` — update profile fields including nickname propagation and age calculation.
- `GET /questionnaires` — list active questionnaires.
- `POST /questionnaires/{slug}/responses` — submit and update questionnaire answers.

## Test isolation

Each test gets a clean state:

- Tables are dropped and recreated from SQLAlchemy metadata.
- PostgreSQL enum types are dropped.
- The `vector` extension is installed.
- Default questionnaires are seeded.
- Redis database `15` is flushed.

## Notes

- The `pyproject.toml` in the backend directory configures `asyncio_mode = "auto"` so async tests run without explicit `@pytest.mark.asyncio` decorators.
- `tests/conftest.py` defines a session-scoped `event_loop` fixture to prevent asyncpg connection-pool / event-loop mismatches between tests. This triggers a deprecation warning from pytest-asyncio 0.23 but is required for stable PostgreSQL integration tests.
- Core source files were modified only to fix test-relevant bugs:
  - Malformed triple-quoted docstrings in several router files (`chat.py`, `discovery.py`, `friends.py`, `profiles.py`).
  - `database.py`: corrected `CREATE EXTENSION` name from `pgvector` to `vector`.
  - `models.py`: added the missing `nickname` column to the `Profile` model.
  - `schemas.py` and `routers/profiles.py`: aligned `ProfileOut` with data sourced from both `Profile` and `User`.
- You may see harmless deprecation warnings from `passlib` and `python-jose` about deprecated stdlib modules; these do not affect test results.
