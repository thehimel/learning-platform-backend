"""API integration tests for POST/DELETE /api/courses/{id}/enroll."""

import pytest


class TestEnrollAPI:
    """Tests for enroll and unenroll endpoints."""

    @pytest.mark.asyncio
    async def test_enroll_returns_201_with_enrollment(self, client, routes):
        """Enroll returns 201 with full enrollment resource."""
        create_resp = await client.post(
            routes.courses_create,
            json={"title": "Enroll Test", "add_me_as_instructor": True, "instructor_ids": []},
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        response = await client.post(routes.courses_enroll(course_id))

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["course_id"] == course_id
        assert "user_id" in data
        assert "enrolled_at" in data

        # Verify enrolled_count increased
        list_resp = await client.get(routes.courses_get)
        assert list_resp.status_code == 200
        course = next(c for c in list_resp.json() if c["id"] == course_id)
        assert course["enrolled_count"] == 1

    @pytest.mark.asyncio
    async def test_enroll_already_enrolled_returns_409(self, client, routes):
        """Enrolling again returns 409 Conflict."""
        create_resp = await client.post(
            routes.courses_create,
            json={"title": "Double Enroll", "add_me_as_instructor": True, "instructor_ids": []},
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        await client.post(routes.courses_enroll(course_id))
        response = await client.post(routes.courses_enroll(course_id))

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "already_enrolled"

    @pytest.mark.asyncio
    async def test_enroll_nonexistent_course_returns_404(self, client, routes):
        """Enrolling in non-existent course returns 404."""
        response = await client.post(routes.courses_enroll(99999))

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "course_not_found"

    @pytest.mark.asyncio
    async def test_unenroll_returns_204(self, client, routes):
        """Student can unenroll from a course."""
        create_resp = await client.post(
            routes.courses_create,
            json={"title": "Unenroll Test", "add_me_as_instructor": True, "instructor_ids": []},
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]
        await client.post(routes.courses_enroll(course_id))

        response = await client.delete(routes.courses_unenroll(course_id))

        assert response.status_code == 204

        list_resp = await client.get(routes.courses_get)
        course = next(c for c in list_resp.json() if c["id"] == course_id)
        assert course["enrolled_count"] == 0

    @pytest.mark.asyncio
    async def test_unenroll_not_enrolled_returns_409(self, client, routes):
        """Unenrolling when not enrolled returns 409 Conflict."""
        create_resp = await client.post(
            routes.courses_create,
            json={"title": "No Enroll", "add_me_as_instructor": True, "instructor_ids": []},
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        response = await client.delete(routes.courses_unenroll(course_id))

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "not_enrolled"

    @pytest.mark.asyncio
    async def test_unenroll_nonexistent_course_returns_404(self, client, routes):
        """Unenrolling from non-existent course returns 404."""
        response = await client.delete(routes.courses_unenroll(99999))

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "course_not_found"
