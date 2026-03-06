# Coding Conventions

Project-wide conventions.

## Module Layout

Each domain module (e.g. `users`, `courses`) follows the same structure:

- `router.py` — HTTP handlers, dependency wiring
- `routes.py` — `RouteName` enum for `url_path_for` (StrEnum, snake_case: `courses_get`, `courses_get_by_id`)
- `schemas.py` — Pydantic request/response models
- `models.py` — SQLAlchemy ORM models
- `service.py` — Business logic (or `manager.py` when using fastapi-users)
- `errors/` — Domain-specific error handling (when needed): `types.py`, `handlers.py`
- `tests/` — Tests for the module (colocated with the code)

When using third-party integrations (e.g. fastapi-users), structure may differ: `users` has `manager.py` instead of `service.py`; `auth` has no `schemas.py` or `models.py` (uses users').

## Schema Naming

- `[Resource]Create` — Request body for creation
- `[Resource]Update` — Request body for partial updates (all fields optional)
- `[Resource]Read` — Response model
- `[Resource][SubResource]Read` — Nested response

Align naming across modules (e.g. `UserRead`, `CourseRead`).

## REST

- `POST` for create returns `201 Created`
- `DELETE` for removal returns `204 No Content` when there is no response body
- Use `response_model` on all endpoints
- Collection create path: `"/"` (not `""`)

### Resource Creation

- Return `201 Created` with the **full created resource** in the response body (not `204 No Content`)
- Do not set `Location` header — avoids maintenance burden when resource paths or authorization change
- Define a `[Resource]Read` schema for the created resource (e.g. `EnrollmentRead`, `CourseRead`)
- Service returns the ORM object; FastAPI serializes via `response_model`
- Example: `POST /courses/{id}/enroll` → `201` with `{"id": 42, "course_id": 5, "user_id": "...", "enrolled_at": "..."}`

### Resource Deletion

- Use `DELETE` for removal (e.g. unenroll, remove membership)
- Return `204 No Content` when there is no response body

### Path Parameters

- Use `id` in route handlers and service layer for resource IDs (e.g. `/{id}`)

### List Endpoints

- Use limit/offset pagination; return `items`, `total`, `limit`, `offset` in the response
- Default limit (e.g. 20), max limit (e.g. 100) as query params
- Optional filters as query params (e.g. `published`, `q` for title search); apply filters in the service layer

## Authentication

- `Depends(current_instructor)` for instructor-protected routes
- `Depends(current_active_user)` for authenticated user routes
- `Depends(current_admin)` for admin-only routes
- `Depends(current_user_optional)` for endpoints that support both authenticated and unauthenticated access (e.g. list courses — public vs. admin/instructor visibility)

## Config

- Settings via `pydantic_settings.BaseSettings` in `app.config`; load from `.env`
- Required vars validated at startup; missing vars print a message and exit
- Test-specific overrides in `conftest.py` via `os.environ.setdefault()` before app imports: `RATING_RECOMPUTE_ASYNC`, `RATE_LIMIT_ENABLED`

## Database

- `Depends(get_db)` for session injection
- Async SQLAlchemy (`AsyncSession`) with asyncpg
- Use `alembic revision --autogenerate` for migrations; do not manually create or edit migration files
- Import all models in `alembic/env.py` so autogenerate detects schema changes
- Use `column_property` with correlated subquery for computed counts (e.g. `enrolled_count`) instead of loading related rows
- Use bulk insert (e.g. `insert(Model).values([...])`) when replacing related records; fetch in same transaction before commit to avoid re-fetch
- Add partial indexes for list endpoints that commonly filter by a condition (e.g. `WHERE published = true` for `get_courses`); use `postgresql_where` and `postgresql_ops` for ordering columns

## Error Handling

- **Centralized handlers** — Domain exceptions are registered on the FastAPI app via `add_exception_handler`, not caught per-route. Routers and dependencies call services and let exceptions propagate; handlers map them to HTTP responses.
- **Domain error module** — Each domain (auth, courses, users) with explicit error handling uses `app/<domain>/errors/`:
  - `types.py` — Error code enum (e.g. `CourseErrorCode`) and base exception (e.g. `CourseError`) with `status_code`, `error_code`, `message`; subclasses define these as class attributes (single source of truth). Use `get_http_message()` and `get_extra_detail()` for dynamic cases.
  - `handlers.py` — One generic handler that reads metadata from the exception; `register_*_exception_handlers(app)` registers all exception types. For third-party exceptions (e.g. `UserNotExists` from fastapi-users), add a dedicated handler that maps to the domain error format.
  - `__init__.py` — Re-exports codes, types, and registration function
- **Registration** — Call `register_*_exception_handlers(app)` at app startup (e.g. in `main.py`) for each domain
- **Structured responses** — Use `error_detail(DomainErrorCode.member, "message", **extra)` from `app.exceptions` when building handler responses

## Import Order

1. Standard library
2. Third-party
3. Local (`app.*`)

Keep all imports at module top; avoid imports inside functions or methods.

## Rate Limiting

- `slowapi` with `SlowAPIMiddleware`; central `Limiter` in `app.limiter.py`
- Default `60/minute` per client IP; configurable via `RATE_LIMIT_ENABLED` (disabled in tests)
- Rate limit exceeded returns `429` with structured `detail`; handler registered on the app
- Per-route limits (e.g. stricter for create/enroll) are optional; use `@limiter.limit()` when needed

## Security

- **IDOR** — Unpublished or non-public resources return 404 for users without access; list endpoints return only public resources
- **Input validation** — `max_length` on text fields; `html.escape()` for user-facing content before storage (XSS mitigation)
- **Mass assignment** — Use `model_config = ConfigDict(extra="forbid")` on update schemas; document intentional field limitation in docstring

## Performance

- Use existence checks (e.g. `exists()`) instead of loading full resources when only checking permission
- Use `BackgroundTasks` for expensive operations that don't need to block the response (e.g. aggregate recompute)
- For update flows that replace related records, use delete + bulk insert; fetch the updated resource in the same transaction before commit to avoid a separate re-fetch

## API Documentation

- `tags=["ResourceName"]` when including routers (e.g. `tags=["Courses"]`)

## Business Logic

- Keep business logic in the `service` layer
- Router handles HTTP concerns only: validation, auth, response shaping (error mapping is centralized in exception handlers)

## Response Serialization

- Services return ORM objects; do not manually build Pydantic response models in the service layer
- Use `response_model` on endpoints — FastAPI serializes the returned ORM through the schema
- For simple 1:1 mappings, use `model_config = ConfigDict(from_attributes=True)` on the Read schema
- For nested or derived fields (e.g. `enrolled_count`, sorted `instructors`), add a `model_validator(mode="before")` that accepts the ORM and returns a dict for the schema
- Router return type hints should match what the service returns (e.g. `-> list[Course]`, `-> Course`), not the response schema

## Code Formatting

- Blank lines between logical groups (validation → create → assign → return)
- Separate fetch, processing, validation, and return blocks with blank lines
- Use blank lines only; no comments purely for visual separation
- Full words for variables and identifiers (e.g. `customer`, `order_id`), not abbreviations (`c`, `o`, `n`)

## Testing

- Domain tests live in `app/<domain>/tests/` (e.g. `app/courses/tests/`)
- Shared fixtures in project root `conftest.py`
- Use the `routes` fixture from `conftest` — it provides paths via `app.url_path_for(RouteName.*)` so tests stay in sync with the app (e.g. `routes.users_me`, `routes.users_by_id(user_id)`, `routes.courses_create`, `routes.auth_login`) — never hardcode URLs
- Route names live in each domain’s `routes.py` (e.g. `app.auth.routes.RouteName`, `app.users.routes.RouteName`, `app.courses.routes.RouteName`) — routers and tests use these enums
- Test DB: `{postgres_db}_test` or `POSTGRES_DB_TEST`; migrations run at session start; optional `--drop-test-db` to drop after run
- E2E tests use `client_e2e` (only `get_db` overridden; real auth via register/login); unit/integration tests use dependency overrides

## API Collection (Bruno)

- `bruno/` mirrors API structure: `auth/`, `users/`, `courses/` with one request file per endpoint (e.g. `course-update.yml`, `course-delete.yml`)
- Use `{{base_url}}`, `{{admin_access_token}}` etc. from `environments/local.yml`
