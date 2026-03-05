# Auth Security Audit

Deep scan of the authentication and authorization layer. Items are grouped by severity and each carries a clear fix path so they can be addressed incrementally.

---

## Critical

### 1. Stateless JWT logout — tokens survive after logout

**File:** `app/auth/backend.py`

`JWTStrategy` is fully stateless. Calling `POST /api/auth/jwt/logout` only instructs the client to discard the token — the server has no record of it and cannot invalidate it. A stolen or leaked token remains valid until its natural expiry.

**Fix options (pick one):**

- Switch to `DatabaseStrategy` (fastapi-users built-in) — stores tokens in the DB and deletes them on logout.
- Add a Redis-backed token blocklist: on logout, write the `jti` claim to Redis with a TTL matching the token's remaining lifetime, and check it on every request.

---

## High

### 2. No password strength validation

**File:** `app/users/manager.py`

`UserManager` does not implement `validate_password`. Any password is accepted, including single-character ones.

**Fix applied:** `validate_password` implemented in `UserManager` using the `password-strength` library. Policy enforces minimum 8 characters, 1 uppercase, 1 digit, 1 special character, and rejects passwords containing the user's email local-part. See `docs/config/auth/password-validation-setup.md`.

---

### 3. `role` and `is_superuser` can go out of sync

**Files:** `app/users/schemas.py`, `app/users/models.py`

`UserAdminUpdate` inherits `BaseUserUpdate`, which exposes `is_superuser`. An admin can set `role=student` and `is_superuser=True` on the same user simultaneously, creating two conflicting authorization identities (the RBAC `role` system and fastapi-users' built-in superuser flag).

**Fix applied:** The `is_superuser` column was dropped from the `user` table entirely. It is replaced by a SQLAlchemy `hybrid_property` on the `User` model that derives its value from `role` — returning `True` when `role == admin`, `False` otherwise. The setter is a no-op so any value sent via the API is silently discarded. `is_superuser` is also hidden from the `UserAdminUpdate` OpenAPI schema. See `docs/config/auth/rbac-setup.md`.

---

### 4. User enumeration on registration

**File:** `app/auth/router.py`

`POST /api/auth/register` returns `400 REGISTER_USER_ALREADY_EXISTS` when an email is already taken, revealing whether that address is registered.

**Accepted risk:** The standard fastapi-users error response is kept intentionally. Enumeration is mitigated by the `60/minute` rate limit on all routes (item 5). If this becomes a concern in future, options are: override the register route to return a generic `201` regardless of outcome, or add CAPTCHA on the client side.

---

### 5. No rate limiting — brute force and registration flooding

**Files:** `app/auth/router.py`, `app/main.py`

Neither login nor registration has rate limiting. Attackers can:

- Brute-force credentials on `POST /api/auth/jwt/login` without restriction.
- Flood the `users` table via repeated `POST /api/auth/register` calls.

**Fix applied:** `slowapi` installed with `SlowAPIMiddleware` registered in `app/main.py`. A central `Limiter` instance in `app/limiter.py` applies a `default_limits` of `60/minute` to all routes automatically — including fastapi-users generated ones — without requiring per-route decorators. See `docs/config/auth/rate-limiting-setup.md`.

---

## Medium

### 6. Users can change their own email without re-verification

**File:** `app/users/schemas.py`

`_PRIVILEGED_UPDATE_FIELDS` does not include `email`. Because `BaseUserUpdate` exposes `email`, a user can silently change their account email to an address they do not own (since email verification is currently disabled).

**Fix applied:** `email` added to `_PRIVILEGED_UPDATE_FIELDS`. It is now stripped from `PATCH /api/users/me` requests and hidden from the OpenAPI schema. Email changes remain available to admins via `PATCH /api/users/{id}`. To re-enable self-service email updates, remove `email` from `_PRIVILEGED_UPDATE_FIELDS` and enable email verification — see `docs/config/auth/email-setup.md`.

---

### 7. `allow_credentials=True` with `CORS_ORIGINS=`* is an invalid combination

**File:** `app/main.py`

The W3C CORS spec prohibits `Access-Control-Allow-Credentials: true` when the origin is `*`. Browsers silently reject such responses. This does not affect the current Bearer-token flow today, but it will break any future cookie-based auth or credentialed preflight request.

**Accepted for development.** `CORS_ORIGINS=*` is intentional in dev. Before deploying to production, set explicit origins via the `CORS_ORIGINS` environment variable in `.env`.

---

## Low / Informational

### 8. No refresh token mechanism

`JWTStrategy` issues access tokens only. There is no silent refresh flow — users must re-authenticate when the token expires.

**Accepted trade-off:** Token expiry increased to 1 day (`jwt_access_token_expire_minutes=1440` in `app/config.py`) to reduce re-login frequency. Longer expiry weakens security if a token is stolen. For stricter security, implement a refresh-token endpoint or switch to a short-lived access + long-lived refresh pattern.

---

### 9. No audit log for privilege escalation

**File:** `app/users/manager.py`

`PATCH /api/users/{id}` allows role promotion (e.g., `student → admin`) but `UserManager` has no dedicated hook that logs the change details.

**Fix applied:** `on_after_update` overridden in `UserManager`. Whenever `role` is present in the update dict, a `WARNING` is logged with the user ID and the new role value.

---

### 10. `auth_dummy_password` defaults to an empty string

**File:** `app/config.py`

The dummy password used for timing-attack mitigation (hashing when a user is not found) defaults to `""`. An empty string hashes near-instantaneously, partially defeating the timing-equalization goal.

**Fix applied:** Default changed to `"timing-equaliser-only"` — a non-empty string that forces bcrypt to run at its normal cost, keeping login timing consistent regardless of whether the user exists.

---

## Checklist


| #   | Issue                                | Severity | Status                                                                                             |
| --- | ------------------------------------ | -------- | -------------------------------------------------------------------------------------------------- |
| 1   | Stateless JWT logout                 | Critical | ⬜ To do                                                                                            |
| 2   | No password strength validation      | High     | ✅ Done — `password-strength` policy in `UserManager.validate_password`                             |
| 3   | `role` / `is_superuser` out of sync  | High     | ✅ Done — `is_superuser` column dropped; replaced by `hybrid_property` derived from `role`          |
| 4   | User enumeration on register         | High     | ✅ Accepted — mitigated by rate limiting; no code change                                            |
| 5   | No rate limiting                     | High     | ✅ Done — `slowapi` `SlowAPIMiddleware` with `60/minute` default on all routes                      |
| 6   | Email change without re-verification | Medium   | ✅ Done — `email` added to `_PRIVILEGED_UPDATE_FIELDS`; re-enable when email verification is set up |
| 7   | Invalid CORS + credentials config    | Medium   | ✅ Accepted for dev — `CORS_ORIGINS` must be set explicitly before production deploy                |
| 8   | No refresh tokens                    | Low      | ✅ Accepted — token expiry set to 1 day; refresh flow deferred                                      |
| 9   | No privilege escalation audit log    | Low      | ✅ Done — `on_after_update` logs a warning whenever `role` changes                                  |
| 10  | Empty dummy password                 | Low      | ✅ Done — default set to `"timing-equaliser-only"`                                                  |


