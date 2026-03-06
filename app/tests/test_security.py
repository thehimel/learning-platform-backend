"""Security tests — auth, authorization, rate limiting, input validation."""

import uuid

import pytest
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.main import app
from app.tests.helpers import e2e_login
from app.users.models import UserRole


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestUnauthenticatedAccess:
    """Unauthenticated access to protected routes returns 401."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,route_attr,payload",
        [
            ("get", "users_me", None),
            ("patch", "users_update_me", {"password": "NewPass1!"}),
            ("get", "users_by_id", None),
            ("patch", "users_update_by_id", {"role": "instructor"}),
            ("delete", "users_delete_by_id", None),
            ("post", "courses_create", {"title": "Course", "add_me_as_instructor": True, "instructor_ids": []}),
            ("post", "courses_enroll", None),
            ("delete", "courses_unenroll", None),
            ("post", "courses_rate", {"rating": 4.5}),
        ],
        ids=["get_me", "patch_me", "get_user", "patch_user", "delete_user", "create_course", "enroll", "unenroll", "rate"],
    )
    async def test_protected_routes_return_401_without_token(
        self, client_e2e, routes, method, route_attr, payload
    ):
        """Protected routes return 401 when no Bearer token is provided."""
        route_fn = getattr(routes, route_attr)
        if "by_id" in route_attr:
            url = route_fn(uuid.uuid4())
        elif route_attr in ("courses_enroll", "courses_unenroll", "courses_rate"):
            url = route_fn(1)
        else:
            url = route_fn

        if method == "get":
            response = await client_e2e.get(url)
        elif method == "patch":
            response = await client_e2e.patch(url, json=payload or {})
        elif method == "delete":
            response = await client_e2e.delete(url)
        else:
            response = await client_e2e.post(url, json=payload or {})

        assert response.status_code == 401


class TestRateLimiting:
    """Rate limiting returns 429 when limit exceeded."""

    @pytest.mark.asyncio
    async def test_login_rate_limit_returns_429(self, client_e2e, routes):
        """Exceeding rate limit on auth endpoint returns 429."""
        # Use a stricter limit for this test to avoid 61 requests
        strict_limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["2/minute"],
        )
        original = app.state.limiter
        app.state.limiter = strict_limiter

        try:
            # First 2 requests get through (any non-429 = not rate limited yet)
            for _ in range(2):
                r = await client_e2e.post(
                    routes.auth_login,
                    data={"username": "a@b.com", "password": "wrong"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                assert r.status_code != 429

            # 3rd request hits rate limit
            r = await client_e2e.post(
                routes.auth_login,
                data={"username": "a@b.com", "password": "wrong"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert r.status_code == 429
        finally:
            app.state.limiter = original


class TestStudentCannotAccessAdminRoutes:
    """Student cannot access admin-only routes (403)."""

    @pytest.mark.asyncio
    async def test_student_cannot_access_admin_user_routes(self, client_e2e, db_session, routes):
        """Student (registered) cannot GET/PATCH/DELETE users."""
        email = f"student-sec-{uuid.uuid4().hex[:8]}@test.example"
        password = "SecurePass1!"

        await client_e2e.post(routes.auth_register, json={"email": email, "password": password})
        token = await e2e_login(client_e2e, email, password, routes.auth_login)

        other_id = uuid.uuid4()

        get_resp = await client_e2e.get(
            routes.users_by_id(other_id),
            headers=_auth_headers(token),
        )
        assert get_resp.status_code == 403

        patch_resp = await client_e2e.patch(
            routes.users_update_by_id(other_id),
            json={"role": UserRole.admin.value},
            headers=_auth_headers(token),
        )
        assert patch_resp.status_code == 403

        delete_resp = await client_e2e.delete(
            routes.users_delete_by_id(other_id),
            headers=_auth_headers(token),
        )
        assert delete_resp.status_code == 403


class TestWeakPasswordRejected:
    """Weak passwords are rejected at registration."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "password",
        [
            "short1!",
            "nouppercase1!",
            "NODIGITS!",
            "NoSpecial123",
        ],
        ids=["short", "no_uppercase", "no_digit", "no_special"],
    )
    async def test_weak_password_registration_returns_400(self, client_e2e, routes, password):
        """Registration with weak password returns 400."""
        email = f"weak-{uuid.uuid4().hex[:8]}@test.example"
        response = await client_e2e.post(
            routes.auth_register,
            json={"email": email, "password": password},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


class TestInputInjection:
    """SQL injection and XSS payloads are handled safely (stored as data, not executed)."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_course_title_stored_safely(
        self, client_e2e, instructor_e2e, routes
    ):
        """Course title with SQL-like payload is stored as string, not executed."""
        _, token = instructor_e2e

        payload = {
            "title": "'; DROP TABLE users; --",
            "add_me_as_instructor": True,
            "instructor_ids": [],
        }
        response = await client_e2e.post(
            routes.courses_create,
            json=payload,
            headers=_auth_headers(token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "'; DROP TABLE users; --"

    @pytest.mark.asyncio
    async def test_xss_payload_in_course_title_stored_safely(
        self, client_e2e, instructor_e2e, routes
    ):
        """Course title with XSS payload is stored as string, not executed."""
        _, token = instructor_e2e

        payload = {
            "title": "<script>alert(1)</script>",
            "add_me_as_instructor": True,
            "instructor_ids": [],
        }
        response = await client_e2e.post(
            routes.courses_create,
            json=payload,
            headers=_auth_headers(token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "<script>alert(1)</script>"
