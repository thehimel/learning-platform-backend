"""API integration tests for GET /api/courses/."""

import pytest


class TestGetCoursesAPI:
    """Tests for the course list endpoint (GET /courses)."""

    @pytest.mark.asyncio
    async def test_get_courses_empty_returns_200(self, client_e2e, routes):
        """GET /courses returns 200 with empty list when no courses exist (public endpoint)."""
        response = await client_e2e.get(routes.courses_get)

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_courses_returns_created_courses(
        self,
        client,
        test_instructor,
        routes,
    ):
        """GET /courses returns courses created by instructor."""
        payload = {
            "title": "Course A",
            "description": "First course",
            "add_me_as_instructor": True,
            "instructor_ids": [],
        }
        create_resp = await client.post(routes.courses_create, json=payload)
        assert create_resp.status_code == 201

        response = await client.get(routes.courses_get)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Course A"
        assert data[0]["description"] == "First course"
        assert data[0]["enrolled_count"] == 0
        assert len(data[0]["instructors"]) == 1
        assert data[0]["instructors"][0]["email"] == test_instructor.email

    @pytest.mark.asyncio
    async def test_get_courses_ordered_by_created_at_desc(
        self,
        client,
        routes,
    ):
        """GET /courses returns courses in reverse chronological order."""
        for title in ["First", "Second", "Third"]:
            payload = {
                "title": title,
                "add_me_as_instructor": True,
                "instructor_ids": [],
            }
            await client.post(routes.courses_create, json=payload)

        response = await client.get(routes.courses_get)

        assert response.status_code == 200
        titles = [c["title"] for c in response.json()]
        assert titles == ["Third", "Second", "First"]
