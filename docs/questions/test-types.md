# Test Types

A concise reference for software test types, with examples from this codebase.

---

## Test Types

### 1. Unit

**What:** Test a single unit (function, class, module) in isolation. Dependencies are mocked or stubbed.

**Characteristics:**
- Fast, no DB, no network
- Test one thing at a time
- High coverage of edge cases

**Example (this project):**
- [app/users/tests/test_manager_unit.py](../../app/users/tests/test_manager_unit.py) — `UserManager.validate_password()` with mocked `user_db`
- [app/courses/tests/test_service_unit.py](../../app/courses/tests/test_service_unit.py) — `_resolve_instructor_ids()` pure function
- [app/tests/test_exceptions.py](../../app/tests/test_exceptions.py) — `error_detail()` helper
- [app/courses/tests/test_schemas.py](../../app/courses/tests/test_schemas.py) — Pydantic schema validation

**Typical questions:**
- What do you mock in unit tests? (DB, external APIs, file I/O)
- How do you test private methods? (Prefer testing via public API; if needed, test indirectly or use `@staticmethod` extraction)

---

### 2. Integration

**What:** Test how multiple components work together. Real or test DB, real app stack; auth/identity often overridden.

**Characteristics:**
- Uses real DB (or test DB), real HTTP layer
- Tests API endpoints with dependency overrides (e.g. `current_instructor`, `get_db`)
- Slower than unit tests

**Example (this project):**
- [app/courses/tests/test_create_course_api.py](../../app/courses/tests/test_create_course_api.py) — POST `/api/courses/` with `client` (instructor override)
- [app/users/tests/test_users_admin_api.py](../../app/users/tests/test_users_admin_api.py) — GET/PATCH/DELETE `/api/users/{id}` with `client_admin`
- [app/users/tests/test_users_me_api.py](../../app/users/tests/test_users_me_api.py) — GET/PATCH `/api/users/me` with `client_users`
- [app/courses/tests/test_create_course_service.py](../../app/courses/tests/test_create_course_service.py) — `create_course` service with real DB session

**Typical questions:**
- How do integration tests differ from E2E? (E2E uses real auth flow; integration often overrides auth)
- How do you isolate integration tests? (Separate test DB, transaction rollback, fixtures)

---

### 3. E2E (End-to-End)

**What:** Test full user flows with minimal mocking. Real auth (register, login), real DB, real HTTP.

**Characteristics:**
- No auth overrides — real JWT login
- Exercises full stack: auth → API → DB
- Slowest, highest confidence

**Example (this project):**
- [app/tests/test_e2e.py](../../app/tests/test_e2e.py) — Register → login → GET `/me`; instructor creates course; admin manages users
- Uses `client_e2e` from [conftest.py](../../conftest.py) (only `get_db` overridden; auth is real)

**Typical questions:**
- When do you use E2E vs integration? (E2E for critical flows; integration for broader endpoint coverage)
- How do you keep E2E tests fast? (Shared fixtures, parallel runs, selective E2E suite)

---

### 4. Security

**What:** Verify auth, authorization, and input validation.

**Example (this project):**
- [app/tests/test_security.py](../../app/tests/test_security.py) — 401 unauthenticated, 429 rate limit, 403 student→admin, weak password rejected, SQL/XSS input handling

**Example scenarios:**
- Unauthenticated access to protected routes → 401
- Rate limiting on `/auth/login` → 429
- Student cannot access admin routes → 403
- Weak password rejected
- SQL injection / XSS in inputs

**Tools:** Bandit, Safety, OWASP ZAP, custom tests.

---

### 5. Smoke

**What:** Minimal checks that the app starts and basic paths respond.

**Use case:** CI/CD, deployment verification.

**Example scenarios:**
- `GET /` returns 200
- `GET /health/db` returns 200 when DB is reachable
- Auth endpoints exist (e.g. 422 for missing body)

---

### 6. Sanity

**What:** Quick, focused checks that core functionality works after a change or fix.

**Use case:** After a small fix or deployment — decide if deeper testing is needed.

**Smoke vs sanity:**
- Smoke: "Does it start?" — broad, app-level
- Sanity: "Does it behave sensibly?" — narrow, feature-level

**Example scenarios:**
- After login fix: register → login → GET `/me` returns 200
- After course fix: instructor can create a course
- After DB migration: `/health/db` returns 200

---

### 7. Contract

**What:** Ensure API behavior matches the OpenAPI schema and Pydantic models.

**Use case:** Prevent breaking changes for clients.

**Tools:** Schemathesis, custom checks against `app.openapi()`.

**Example scenarios:**
- Request/response bodies match schemas
- Status codes and error formats match spec

---

### 8. Performance

**What:** Measure response times and throughput under load.

**Use case:** Ensure acceptable latency and capacity.

**Tools:** Locust, pytest-benchmark, k6.

---

### 8. Resilience

**What:** Test behavior when dependencies fail.

**Example scenarios:**
- DB unreachable → `/health/db` returns 5xx
- Timeouts on external calls
- Graceful degradation

---

### 10. Snapshot

**What:** Compare API responses to stored snapshots to detect unintended changes.

**Tools:** Syrupy, pytest-snapshot.

---

## Test Pyramid (Conceptual)

```
        /\
       /  \     E2E (few, high confidence)
      /----\
     /      \   Integration (more, medium confidence)
    /--------\
   /          \ Unit (many, fast, high coverage)
  /------------\
```

- **Unit:** Many, fast, isolated
- **Integration:** Moderate number, real DB/HTTP, overridden auth
- **E2E:** Few, full stack, real auth

---

## Quick Reference

| Type        | DB      | Auth           | Speed   | Confidence |
|-------------|---------|----------------|---------|------------|
| Unit        | Mocked  | N/A            | Fast    | Medium     |
| Integration | Real    | Overridden     | Medium  | High       |
| E2E         | Real    | Real (login)   | Slow    | Highest    |
| Security    | Varies  | Varies         | Medium  | High       |
| Smoke       | Optional| N/A            | Fast    | Low        |
| Sanity      | Optional| Optional       | Fast    | Low        |
| Contract    | Optional| Optional       | Medium  | Medium     |

---

## This Project's Test Layout

Ordered by type: Unit → Integration → E2E → Security → Smoke → Sanity → Contract.

| Path | Type |
|------|------|
| [app/tests/test_exceptions.py](../../app/tests/test_exceptions.py) | Unit |
| [app/users/tests/test_manager_unit.py](../../app/users/tests/test_manager_unit.py) | Unit |
| [app/courses/tests/test_service_unit.py](../../app/courses/tests/test_service_unit.py) | Unit |
| [app/courses/tests/test_schemas.py](../../app/courses/tests/test_schemas.py) | Unit |
| [app/courses/tests/test_create_course_api.py](../../app/courses/tests/test_create_course_api.py) | Integration |
| [app/users/tests/test_users_admin_api.py](../../app/users/tests/test_users_admin_api.py) | Integration |
| [app/users/tests/test_users_me_api.py](../../app/users/tests/test_users_me_api.py) | Integration |
| [app/courses/tests/test_create_course_service.py](../../app/courses/tests/test_create_course_service.py) | Integration (service + DB) |
| [app/tests/test_e2e.py](../../app/tests/test_e2e.py) | E2E |
| [app/tests/helpers.py](../../app/tests/helpers.py) | Shared E2E helpers |
| [app/tests/test_security.py](../../app/tests/test_security.py) | Security |
