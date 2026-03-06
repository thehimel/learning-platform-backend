"""API integration tests for POST /api/courses/."""

import pytest


class TestCreateCourseAPI:
    """Tests for the course creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_course_with_self_as_instructor_returns_201(
        self,
        client,
        test_instructor,
        routes,
    ):
        """Creating a course with add_me_as_instructor=true returns 201 with full course resource."""
        payload = {
            "title": "Introduction to Python",
            "description": "Learn Python basics",
            "add_me_as_instructor": True,
            "instructor_ids": [],
        }

        response = await client.post(routes.courses_create, json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Introduction to Python"
        assert data["description"] == "Learn Python basics"
        assert data["published"] is False
        assert data["rating"] is None
        assert data["enrolled_count"] == 0
        assert len(data["instructors"]) == 1
        assert data["instructors"][0]["id"] == str(test_instructor.id)
        assert data["instructors"][0]["email"] == test_instructor.email
        assert data["instructors"][0]["is_primary"] is True

    @pytest.mark.asyncio
    async def test_create_course_without_self_adds_only_provided_instructors(
        self,
        client,
        test_instructor,
        routes,
    ):
        """When add_me_as_instructor=false, only instructor_ids are used."""
        payload = {
            "title": "Advanced Topics",
            "add_me_as_instructor": False,
            "instructor_ids": [str(test_instructor.id)],
        }

        response = await client.post(routes.courses_create, json=payload)

        assert response.status_code == 201
        data = response.json()
        assert len(data["instructors"]) == 1
        assert data["instructors"][0]["id"] == str(test_instructor.id)

    @pytest.mark.asyncio
    async def test_create_course_invalid_instructor_ids_returns_400(
        self,
        client,
        routes,
    ):
        """Invalid or non-instructor user IDs return 400 with structured error."""
        import uuid

        payload = {
            "title": "Test Course",
            "add_me_as_instructor": False,
            "instructor_ids": [str(uuid.uuid4())],
        }

        response = await client.post(routes.courses_create, json=payload)

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "invalid_instructor_ids"
        assert "missing_ids" in data["detail"]
        assert len(data["detail"]["missing_ids"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"title": "Test Course", "add_me_as_instructor": False, "instructor_ids": []},
            {"title": "", "add_me_as_instructor": True, "instructor_ids": []},
        ],
        ids=["no_instructor", "empty_title"],
    )
    async def test_create_course_validation_errors_return_422(self, client, routes, payload):
        """Invalid payload returns 422."""
        response = await client.post(routes.courses_create, json=payload)
        assert response.status_code == 422
