"""API integration tests for POST /api/courses/{id}/rate."""

import pytest


class TestRateAPI:
    """Tests for the rate course endpoint."""

    @pytest.mark.asyncio
    async def test_rate_returns_204(self, client, routes):
        """User can rate a course."""
        create_resp = await client.post(
            routes.courses_create,
            json={"title": "Rate Test", "add_me_as_instructor": True, "instructor_ids": []},
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        response = await client.post(routes.courses_rate(course_id), json={"rating": 4.5})

        assert response.status_code == 204

        list_resp = await client.get(routes.courses_get)
        course = next(c for c in list_resp.json() if c["id"] == course_id)
        assert course["rating"] == 4.5

    @pytest.mark.asyncio
    async def test_rate_upsert_updates_existing(self, client, routes):
        """Rating again updates the existing rating."""
        create_resp = await client.post(
            routes.courses_create,
            json={"title": "Upsert Rate", "add_me_as_instructor": True, "instructor_ids": []},
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        await client.post(routes.courses_rate(course_id), json={"rating": 3.0})
        response = await client.post(routes.courses_rate(course_id), json={"rating": 5.0})

        assert response.status_code == 204

        list_resp = await client.get(routes.courses_get)
        course = next(c for c in list_resp.json() if c["id"] == course_id)
        assert course["rating"] == 5.0

    @pytest.mark.asyncio
    async def test_rate_nonexistent_course_returns_404(self, client, routes):
        """Rating non-existent course returns 404."""
        response = await client.post(routes.courses_rate(99999), json={"rating": 4.0})

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "course_not_found"

    @pytest.mark.asyncio
    async def test_rate_invalid_returns_422(self, client, routes):
        """Rating outside 1–5 returns 422."""
        create_resp = await client.post(
            routes.courses_create,
            json={"title": "Invalid Rate", "add_me_as_instructor": True, "instructor_ids": []},
        )
        assert create_resp.status_code == 201
        course_id = create_resp.json()["id"]

        response = await client.post(routes.courses_rate(course_id), json={"rating": 6.0})

        assert response.status_code == 422
