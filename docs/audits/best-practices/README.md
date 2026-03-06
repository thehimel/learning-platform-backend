# Suggested Conventions & Best Practices

Candidates to add to `docs/conventions.md` or adopt as project standards.

---

## Testing

| Practice | Status | Notes |
|----------|--------|-------|
| **Test naming** | Consider | `test_<action>_<expected>_<condition>` (e.g. `test_create_course_returns_201_when_valid`) |
| **One assertion per test** | Optional | Prefer single logical assertion; multiple related asserts are acceptable |
| **Coverage** | Add | `pytest-cov`; report in CI; aim for ≥80% on critical paths |
| **Test isolation** | ✓ | Done — transaction rollback per test |
| **Test pyramid** | Consider | More unit tests, fewer integration tests |
| **Markers** | Add | `@pytest.mark.slow`, `@pytest.mark.integration` for selective runs |
| **Constants** | Consider | Extract magic strings (e.g. `"TestPass1!"`) to `conftest` or fixtures |

---

## Code Quality

| Practice | Status | Notes |
|----------|--------|-------|
| **Type hints** | Add | `mypy` or `pyright` in CI; strict mode for new code |
| **Docstrings** | Consider | Public API (routers, services) — Google or NumPy style |
| **Ruff linter rules** | Add | `pytest-cov`, `ruff` select rules (e.g. `I`, `E`, `F`, `B`) |
| **Pre-commit** | ✓ | Done — ruff, ruff-format |

---

## CI/CD

| Practice | Status | Notes |
|----------|--------|-------|
| **Test on push** | Add | GitHub Actions / GitLab CI — run pytest |
| **Lint on push** | Add | Run `ruff check` and `ruff format --check` |
| **Coverage gate** | Add | Fail if coverage drops below threshold |
| **Matrix build** | Consider | Test against Python 3.14 (and 3.13 if needed) |

---

## Security

| Practice | Status | Notes |
|----------|--------|-------|
| **Secrets** | ✓ | Use `.env`; no secrets in code |
| **Dependency audit** | Add | `pip-audit` or `safety` in CI |
| **Rate limiting** | ✓ | Done — slowapi |

---

## API

| Practice | Status | Notes |
|----------|--------|-------|
| **Versioning** | Consider | `/api/v1/` prefix for future breaking changes |
| **Pagination** | Consider | Add when listing endpoints exist |
| **Request IDs** | Consider | `X-Request-ID` for tracing |
| **Health check** | Add | `GET /health` for load balancers / k8s |

---

## Database

| Practice | Status | Notes |
|----------|--------|-------|
| **Migrations** | ✓ | Alembic |
| **Test DB** | ✓ | Separate `{postgres_db}_test` DB; auto-create and migrate before pytest |
| **Connection pool** | ✓ | SQLAlchemy configured |

---

## Documentation

| Practice | Status | Notes |
|----------|--------|-------|
| **OpenAPI** | ✓ | FastAPI auto-generates |
| **README** | Consider | Quick start, setup, run commands |
| **Changelog** | Consider | `CHANGELOG.md` for releases |

---

## Performance & Optimization

| Practice | Status | Notes |
|----------|--------|-------|
| **Connection pooling** | ✓ | SQLAlchemy pool; tune `pool_size`, `max_overflow` per load |
| **Eager loading** | Add | Use `selectinload`/`joinedload` to avoid N+1 queries; avoid lazy loads in async |
| **Query batching** | Consider | Batch related reads; use `execution_options(stream_results=True)` for large result sets |
| **Response compression** | Add | `GZipMiddleware` for JSON responses |
| **Async all the way** | ✓ | AsyncSession, asyncpg; avoid blocking calls in request path |
| **Indexes** | Add | Index FK columns, frequently filtered/sorted columns; review `EXPLAIN ANALYZE` |
| **Payload size** | Consider | Limit request body size; paginate list responses |
| **SQL echo off** | ✓ | `sql_echo=False` in prod |

---

## Scalability

| Practice | Status | Notes |
|----------|--------|-------|
| **Stateless app** | ✓ | No in-memory session; JWT or external session store |
| **Horizontal scaling** | ✓ | Multiple app instances behind load balancer |
| **DB connection limits** | Add | `pool_size` ≤ DB `max_connections` / app_instances |
| **Read replicas** | Consider | Route reads to replica; use `AsyncSession` with different bind |
| **Background tasks** | Add | Offload email, notifications to Celery/RQ/ARQ |
| **Event-driven** | Consider | Message queue (Redis/RabbitMQ) for async workflows |
| **CQRS** | Consider | Separate read/write models for high-read domains |

---

## Caching

| Practice | Status | Notes |
|----------|--------|-------|
| **Response caching** | Add | Cache GET by path+query; Redis or in-memory; set TTL |
| **HTTP cache headers** | Add | `Cache-Control`, `ETag` for static/list responses |
| **Application cache** | Consider | Cache hot data (e.g. config, lookup tables) in memory |
| **Cache invalidation** | Consider | Invalidate on write; use versioned keys or tags |
| **Stale-while-revalidate** | Consider | Serve stale, refresh in background |

---

## Observability & Monitoring

| Practice | Status | Notes |
|----------|--------|-------|
| **Structured logging** | ✓ | JSON logs; include `request_id`, `user_id`, `duration` |
| **Metrics** | Add | Prometheus/StatsD — request latency, error rate, DB pool usage |
| **Tracing** | Consider | OpenTelemetry for distributed tracing |
| **APM** | Consider | Sentry, Datadog for errors and performance |
| **Slow query log** | Add | Log queries > N ms; use SQLAlchemy events |
| **Health checks** | Add | `/health` (liveness), `/ready` (DB + deps) for k8s |

---

## Resource Management

| Practice | Status | Notes |
|----------|--------|-------|
| **Connection lifecycle** | ✓ | `async with` for sessions; proper teardown |
| **Memory** | Consider | Stream large responses; avoid loading full result sets |
| **Timeouts** | Add | DB query timeout; HTTP client timeout for outbound calls |
| **Graceful shutdown** | Consider | Drain in-flight requests; close DB pool on SIGTERM |
| **Resource limits** | Consider | Limit concurrent requests per user/IP |

---

## Suggested Priority

**High (implement soon):**
- Coverage reporting (`pytest-cov`)
- CI pipeline (tests + lint)
- Health check endpoint
- Eager loading (avoid N+1)

**Medium:**
- Type checker (mypy)
- Test markers (`@pytest.mark.integration`)
- Test DB env var for CI
- Response compression
- Connection pool tuning
- Metrics / slow query log

**Low:**
- API versioning
- Docstrings
- Changelog
- Read replicas
- Caching layer
- Background tasks
