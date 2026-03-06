# Commands

## Management

```shell
uvicorn app.main:app --reload
```

### Health check

```shell
# Verify API is running
curl http://localhost:8000/

# Verify database connectivity
curl http://localhost:8000/health/db
```

## Docker

### Build and Run (standalone)

```shell
# Build the image with a custom tag
docker build -t learning-platform-api .

# Run the container (interactive, remove on exit)
docker run -it --rm --name learning-platform-api learning-platform-api
```

### Run a Single Python Script

```shell
# Mount current directory and run a script (replace your-demon-script.py with your file)
docker run -it --rm -v "$PWD":/usr/src/app -w /usr/src/app python:3.14 python your-demon-script.py
```

### Inspect Container Filesystem

```shell
# Open a shell in the running API container (use container name from docker compose ps)
docker exec -it learning-platform-api bash

# Verify bind mount: check that local files are available
cat app/main.py
```

## Docker Compose

### PostgreSQL only (existing)

```shell
# Start PostgreSQL in the background
docker compose up -d

# Check service status
docker compose ps

# Stop PostgreSQL
docker compose down

# Stop and remove the database volume (deletes data)
docker compose down -v

# Create database if missing (e.g. after changing POSTGRES_DB in .env)
docker compose exec postgres psql -U postgres -c "CREATE DATABASE \"learning-platform\";"

# Verify connection from host (replace DB name if different)
docker compose exec postgres psql -U postgres -d learning-platform -c "SELECT 1;"

# Inspect PostgreSQL logs
docker compose logs postgres
```

### Development (API + PostgreSQL, bind mount, --reload)

```shell
# Start API and PostgreSQL
docker compose -f docker-compose.dev.yml up -d

# Rebuild after Dockerfile changes (--build forces a rebuild so Dockerfile changes are reflected)
docker compose -f docker-compose.dev.yml up --build -d

# View logs
docker compose -f docker-compose.dev.yml logs -f api

# Stop
docker compose -f docker-compose.dev.yml down
```

### Production (API + PostgreSQL, no bind mount, port 80)

```shell
# Start API and PostgreSQL (ensure .env has production values)
docker compose -f docker-compose.prod.yml up -d

# Rebuild after Dockerfile changes (--build forces a rebuild so Dockerfile changes are reflected)
docker compose -f docker-compose.prod.yml up --build -d

# Stop
docker compose -f docker-compose.prod.yml down
```

### Compose Logs (all services)

```shell
# View logs from all services (use -f to follow)
docker compose -f docker-compose.dev.yml logs
docker compose -f docker-compose.dev.yml logs -f
```

### Docker Hub (push image)

```shell
# Build the image first (if not already built)
docker compose -f docker-compose.dev.yml build

# Log in to Docker Hub
docker login

# Tag the locally built image (replace username with your Docker Hub username)
# Image name is typically project_service, e.g. learning-platform-api_api
docker image tag learning-platform-api_api username/fastapi

# Verify the tag
docker image ls

# Push the image to Docker Hub
docker push username/fastapi
```

**Note:** For production, `docker-compose.prod.yml` can reference `image: username/fastapi` instead of `build: .` to use the pushed image.

## Alembic

Run from the project root. See [Alembic Setup](config/sqlalchemy-alembic-async-setup.md) for full guide.

| Alembic | Purpose | Django equivalent |
|---------|---------|-------------------|
| `alembic init alembic` | Initialize Alembic (creates `alembic/` and `alembic.ini`; `alembic` is the directory name) | — |
| `alembic revision --autogenerate -m "message"` | Create migration from model changes | `python manage.py makemigrations` |
| `alembic revision -m "message"` | Create manual migration (no autogenerate) | `python manage.py makemigrations` |
| `alembic upgrade head` | Apply all pending migrations | `python manage.py migrate` |
| `alembic upgrade <revision>` | Upgrade to a specific revision | `python manage.py migrate <app> <revision>` |
| `alembic downgrade -1` | Roll back one revision | `python manage.py migrate <app> <prev_rev>` |
| `alembic downgrade <revision>` | Roll back to a specific revision | `python manage.py migrate <app> <revision>` |
| `alembic current` | Show current revision | `python manage.py showmigrations` |
| `alembic heads` | Show latest (head) migration | `python manage.py showmigrations` |
| `alembic history` | List migration history | `python manage.py showmigrations` |

**Note:** `alembic downgrade -N` works for any negative N (e.g. `-2`, `-3`) to roll back multiple revisions. For branched migrations, prefer `alembic downgrade <revision>` with a specific revision ID.

Verify applied migrations in PostgreSQL:

```shell
docker compose exec postgres psql -U postgres -d learning-platform -c "SELECT * FROM public.alembic_version ORDER BY version_num ASC;"
```

## Ruff

```shell
# Lint
ruff check .

# Format
ruff format .

# Lint with auto-fix
ruff check . --fix

# Lint and format specific path
ruff check app/
ruff format app/
```

## Pytest

Run from the project root. The test database (`{POSTGRES_DB}_test`, or `POSTGRES_DB_TEST` if set) is **auto-created** before tests and migrations are run automatically. No manual setup required.

```shell
# Run all tests (minimal output)
pytest

# List each test function (verbose)
pytest -v

# Show print statements (disable output capture; useful when debugging)
pytest -v -s

# Stop on first failure (useful when debugging)
pytest -x

# Drop the test database after the run (clean teardown)
pytest --drop-test-db

# Show create/teardown log messages
pytest --log-cli-level=INFO

# Suppress warning messages
pytest --disable-warnings

# Explore all available options
pytest --help
```

## Pre-commit

```shell
# Install pre-commit hooks (run once)
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files

# Run pre-commit on staged files only (default when run on commit)
pre-commit run
```

## JWT

```shell
# Generate a secure secret key for JWT (set as JWT_SECRET_KEY in .env)
openssl rand -hex 32
```

## Install Dependencies

```shell
# Install all project dependencies
pip install -r requirements.txt
```
