# Troubleshoot database connection

When a client (IDE, GUI tool, or app) fails to connect to the PostgreSQL instance from [docker-compose.yml](../docker-compose.yml) with a generic error, work through the following.

## 1. Container not running

Start the stack and confirm the service is up:

```shell
docker compose up -d
docker compose ps
```

The **postgres** service should show as running.

## 2. Database missing (existing volume)

Postgres creates **POSTGRES_DB** only on first initialization. If the volume was created when `.env` had a different **POSTGRES_DB** (e.g. `fastapi_db`), the current database name (e.g. `learning-platform`) may not exist.

**Option A — create the database:**

```shell
docker compose exec postgres psql -U postgres -c "CREATE DATABASE \"learning-platform\";"
```

**Option B — reset data** (removes all data in the volume):

```shell
docker compose down -v
docker compose up -d
```

## 3. Password

Use the same value as **POSTGRES_PASSWORD** in [.env](../.env.example) (e.g. `postgres`). No leading or trailing spaces.

## 4. Port in use

If another process is using **5432**, either stop it or set **POSTGRES_PORT** in `.env` to a different port and use that port in the client.

## 5. Verify from the host

Confirm the database accepts connections:

```shell
docker compose exec postgres psql -U postgres -d learning-platform -c "SELECT 1;"
```

If this succeeds, the problem is in the client (password, SSL, or firewall). If it fails, inspect logs:

```shell
docker compose logs postgres
```

See [commands.md](commands.md) for Docker Compose commands.
