# Learning Platform API

[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1a1a1a?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)

A learning platform API built with FastAPI. Supports courses, enrollments, ratings, and role-based access (student, instructor, admin).

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (async via asyncpg)
- **ORM:** SQLAlchemy 2.0 (async)
- **Auth:** fastapi-users (JWT)
- **Rate limiting:** slowapi

## Features

- **Auth** — Register, login (JWT), password update
- **Users** — `GET/PATCH /me`; admin CRUD for users
- **Courses** — CRUD, list with pagination and filters (`published`, `q` for title search)
- **Enrollments** — Enroll/unenroll in courses
- **Ratings** — Rate courses (1–5); aggregate recomputed asynchronously
- **Visibility** — Unauthenticated: published only; instructor: published + own unpublished; admin: all

## Prerequisites

- Python 3.14+
- PostgreSQL
- Docker (optional, for running PostgreSQL)

## Quick Start

### 1. Clone and install

```shell
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and set required variables:

```shell
cp .env.example .env
```

Required: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET_KEY`, `AUTH_RESET_PASSWORD_TOKEN_SECRET`, `AUTH_VERIFICATION_TOKEN_SECRET`. Generate secrets with `openssl rand -hex 32`.

### 3. Start PostgreSQL

```shell
docker compose up -d
```

### 4. Run migrations

```shell
alembic upgrade head
```

### 5. Start the API

```shell
uvicorn app.main:app --reload
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

## Commands

| Command | Purpose |
|---------|---------|
| `uvicorn app.main:app --reload` | Run API (dev) |
| `alembic upgrade head` | Apply migrations |
| `alembic revision --autogenerate -m "message"` | Create migration |
| `pytest` | Run tests |
| `pytest --drop-test-db` | Run tests and drop test DB after |
| `ruff check .` | Lint |
| `ruff format .` | Format |

See [docs/commands.md](docs/commands.md) for Docker, pre-commit, and more.

## API Overview

Interactive API docs: http://localhost:8000/docs

## Testing

Tests use a separate DB (`{postgres_db}_test`). Migrations run automatically before tests.

```shell
pytest -v
```

Unit, integration, E2E, security, and smoke tests. See [docs/questions/test-types.md](docs/questions/test-types.md).

## Documentation

- [Conventions](docs/conventions.md) — Coding standards
- [Commands](docs/commands.md) — Docker, Alembic, pytest, ruff
- [DB setup](docs/config/sqlalchemy-alembic-async-setup.md) — Alembic async
- [Auth setup](docs/config/auth/fastapi-users-setup.md) — fastapi-users
- [Test types](docs/questions/test-types.md) — Unit, integration, E2E
