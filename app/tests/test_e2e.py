"""End-to-end tests — full auth flow (register, login) with no dependency overrides for auth."""

import uuid

import pytest

from app.tests.helpers import e2e_login
from app.users.models import UserRole


def _auth_headers(token: str) -> dict:
    """Headers with Bearer token."""
    return {"Authorization": f"Bearer {token}"}


class TestE2EAuthFlow:
    """E2E: register -> login -> authenticated requests."""

    @pytest.mark.asyncio
    async def test_register_login_get_me(self, client_e2e, routes):
        """Register user, login, GET /me returns user data."""
        email = f"e2e-{uuid.uuid4().hex[:8]}@test.example"
        password = "SecurePass1!"

        # Register
        reg = await client_e2e.post(
            routes.auth_register,
            json={"email": email, "password": password},
        )
        assert reg.status_code == 201
        user_id = reg.json()["id"]

        # Login
        token = await e2e_login(client_e2e, email, password, routes.auth_login)

        # GET /me
        me = await client_e2e.get(routes.users_me, headers=_auth_headers(token))
        assert me.status_code == 200
        data = me.json()
        assert data["id"] == user_id
        assert data["email"] == email
        assert data["role"] == UserRole.student.value

    @pytest.mark.asyncio
    async def test_register_login_patch_me(self, client_e2e, routes):
        """Register, login, PATCH /me updates password."""
        email = f"e2e-{uuid.uuid4().hex[:8]}@test.example"
        password = "SecurePass1!"
        new_password = "NewSecure1!"

        await client_e2e.post(routes.auth_register, json={"email": email, "password": password})
        token = await e2e_login(client_e2e, email, password, routes.auth_login)

        patch = await client_e2e.patch(
            routes.users_update_me,
            json={"password": new_password},
            headers=_auth_headers(token),
        )
        assert patch.status_code == 200

        # Login with new password works
        token2 = await e2e_login(client_e2e, email, new_password, routes.auth_login)
        assert token2

    @pytest.mark.asyncio
    async def test_unauthenticated_get_me_returns_401(self, client_e2e, routes):
        """GET /me without token returns 401."""
        response = await client_e2e.get(routes.users_me)
        assert response.status_code == 401


class TestE2EInstructorFlow:
    """E2E: instructor (created in DB) -> login -> create course."""

    @pytest.mark.asyncio
    async def test_student_cannot_create_course(self, client_e2e, routes):
        """Student (registered) cannot POST /courses."""
        email = f"e2e-{uuid.uuid4().hex[:8]}@test.example"
        password = "SecurePass1!"

        await client_e2e.post(routes.auth_register, json={"email": email, "password": password})
        token = await e2e_login(client_e2e, email, password, routes.auth_login)

        response = await client_e2e.post(
            routes.courses_create,
            json={
                "title": "Student Course",
                "add_me_as_instructor": True,
                "instructor_ids": [],
            },
            headers=_auth_headers(token),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_instructor_invalid_instructor_ids_returns_400(self, client_e2e, instructor_e2e, routes):
        """Instructor creates course with invalid instructor_ids returns 400."""
        _, token = instructor_e2e

        payload = {
            "title": "E2E Course",
            "add_me_as_instructor": False,
            "instructor_ids": [str(uuid.uuid4())],
        }
        response = await client_e2e.post(
            routes.courses_create,
            json=payload,
            headers=_auth_headers(token),
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "invalid_instructor_ids"
        assert "missing_ids" in data["detail"]

    @pytest.mark.asyncio
    async def test_instructor_login_create_course(self, client_e2e, instructor_e2e, routes):
        """Instructor logs in and creates a course."""
        instructor, token = instructor_e2e

        payload = {
            "title": "E2E Course",
            "description": "Created via E2E",
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
        assert data["title"] == "E2E Course"
        assert len(data["instructors"]) == 1
        assert data["instructors"][0]["email"] == instructor.email

    @pytest.mark.asyncio
    async def test_student_enroll_and_unenroll(self, client_e2e, instructor_e2e, routes):
        """Student registers, logs in, enrolls in course, then unenrolls."""
        # Instructor creates course
        _, instructor_token = instructor_e2e
        create_resp = await client_e2e.post(
            routes.courses_create,
            json={"title": "E2E Enroll Course", "add_me_as_instructor": True, "instructor_ids": []},
            headers=_auth_headers(instructor_token),
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        # Student registers and logs in
        email = f"e2e-student-{uuid.uuid4().hex[:8]}@test.example"
        password = "SecurePass1!"
        await client_e2e.post(routes.auth_register, json={"email": email, "password": password})
        student_token = await e2e_login(client_e2e, email, password, routes.auth_login)

        # Student enrolls
        enroll_resp = await client_e2e.post(
            routes.courses_enroll(course_id),
            headers=_auth_headers(student_token),
        )
        assert enroll_resp.status_code == 204

        # Verify enrolled_count
        list_resp = await client_e2e.get(routes.courses_get)
        course = next(c for c in list_resp.json() if c["id"] == course_id)
        assert course["enrolled_count"] == 1

        # Student unenrolls
        unenroll_resp = await client_e2e.delete(
            routes.courses_unenroll(course_id),
            headers=_auth_headers(student_token),
        )
        assert unenroll_resp.status_code == 204

        list_resp2 = await client_e2e.get(routes.courses_get)
        course2 = next(c for c in list_resp2.json() if c["id"] == course_id)
        assert course2["enrolled_count"] == 0

    @pytest.mark.asyncio
    async def test_student_rate_course(self, client_e2e, instructor_e2e, routes):
        """Student rates a course, then updates rating."""
        _, instructor_token = instructor_e2e
        create_resp = await client_e2e.post(
            routes.courses_create,
            json={"title": "E2E Rate Course", "add_me_as_instructor": True, "instructor_ids": []},
            headers=_auth_headers(instructor_token),
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        email = f"e2e-rater-{uuid.uuid4().hex[:8]}@test.example"
        password = "SecurePass1!"
        await client_e2e.post(routes.auth_register, json={"email": email, "password": password})
        token = await e2e_login(client_e2e, email, password, routes.auth_login)

        rate_resp = await client_e2e.post(
            routes.courses_rate(course_id),
            json={"rating": 4.0},
            headers=_auth_headers(token),
        )
        assert rate_resp.status_code == 204

        list_resp = await client_e2e.get(routes.courses_get)
        course = next(c for c in list_resp.json() if c["id"] == course_id)
        assert course["rating"] == 4.0

        await client_e2e.post(
            routes.courses_rate(course_id),
            json={"rating": 5.0},
            headers=_auth_headers(token),
        )
        list_resp2 = await client_e2e.get(routes.courses_get)
        course2 = next(c for c in list_resp2.json() if c["id"] == course_id)
        assert course2["rating"] == 5.0


class TestE2EAdminFlow:
    """E2E: admin (created in DB) -> login -> manage users."""

    @pytest.mark.asyncio
    async def test_admin_get_user(self, client_e2e, admin_other_e2e, routes):
        """Admin logs in and GETs another user by id."""
        admin, other, token = admin_other_e2e

        response = await client_e2e.get(
            routes.users_by_id(other.id),
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(other.id)
        assert response.json()["email"] == other.email

    @pytest.mark.asyncio
    async def test_admin_patch_user(self, client_e2e, admin_other_e2e, routes):
        """Admin logs in and PATCHes another user's role."""
        _, other, token = admin_other_e2e

        response = await client_e2e.patch(
            routes.users_update_by_id(other.id),
            json={"role": UserRole.instructor.value},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["role"] == UserRole.instructor.value

    @pytest.mark.asyncio
    async def test_admin_delete_user(self, client_e2e, admin_other_e2e, routes):
        """Admin logs in and DELETEs another user."""
        _, other, token = admin_other_e2e

        response = await client_e2e.delete(
            routes.users_delete_by_id(other.id),
            headers=_auth_headers(token),
        )
        assert response.status_code == 204

        get_resp = await client_e2e.get(
            routes.users_by_id(other.id),
            headers=_auth_headers(token),
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(self, client_e2e, admin_e2e, routes):
        """Admin cannot DELETE their own account."""
        admin, token = admin_e2e

        response = await client_e2e.delete(
            routes.users_delete_by_id(admin.id),
            headers=_auth_headers(token),
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_get_nonexistent_user_returns_404(self, client_e2e, admin_e2e, routes):
        """Admin GET non-existent user returns 404."""
        _, token = admin_e2e

        response = await client_e2e.get(
            routes.users_by_id(uuid.uuid4()),
            headers=_auth_headers(token),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,route_attr,payload",
        [
            ("get", "users_by_id", None),
            ("patch", "users_update_by_id", {"role": UserRole.admin.value}),
            ("delete", "users_delete_by_id", None),
        ],
        ids=["get", "patch", "delete"],
    )
    async def test_instructor_cannot_access_admin_routes(
        self, client_e2e, instructor_other_e2e, routes, method, route_attr, payload
    ):
        """Instructor cannot GET/PATCH/DELETE users (admin-only)."""
        _, other, token = instructor_other_e2e
        route_fn = getattr(routes, route_attr)
        url = route_fn(other.id)

        if method == "get":
            response = await client_e2e.get(url, headers=_auth_headers(token))
        elif method == "patch":
            response = await client_e2e.patch(url, json=payload, headers=_auth_headers(token))
        else:
            response = await client_e2e.delete(url, headers=_auth_headers(token))

        assert response.status_code == 403
