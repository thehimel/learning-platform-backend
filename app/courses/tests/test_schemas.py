"""Unit tests for course schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.courses.schemas import CourseCreate, CourseRate, MAX_INSTRUCTORS_PER_COURSE


class TestCourseRate:
    """Tests for CourseRate schema validation."""

    def test_valid_rating(self):
        """Valid rating 1–5."""
        payload = CourseRate(rating=4.5)
        assert payload.rating == 4.5

    def test_rounds_to_one_decimal(self):
        """Rating is rounded to one decimal place."""
        payload = CourseRate.model_validate({"rating": 4.567})
        assert payload.rating == 4.6

    @pytest.mark.parametrize("rating", [0.5, 5.5, -1, 10], ids=["below_min", "above_max", "negative", "too_high"])
    def test_invalid_rating_raises(self, rating):
        """Rating outside 1–5 raises ValidationError."""
        with pytest.raises(ValidationError):
            CourseRate(rating=rating)


class TestCourseCreate:
    """Tests for CourseCreate schema validation."""

    def test_valid_minimal_payload(self):
        """Minimal valid payload with add_me_as_instructor=True."""
        payload = CourseCreate(
            title="Valid Course",
            add_me_as_instructor=True,
            instructor_ids=[],
        )
        assert payload.title == "Valid Course"
        assert payload.add_me_as_instructor is True
        assert payload.instructor_ids == []

    def test_valid_with_instructor_ids(self):
        """Valid payload with external instructor IDs."""
        instructor_id = uuid.uuid4()
        payload = CourseCreate(
            title="Course with Others",
            add_me_as_instructor=False,
            instructor_ids=[instructor_id],
        )
        assert payload.instructor_ids == [instructor_id]

    def test_dedupe_instructor_ids(self):
        """Duplicate instructor_ids are deduplicated."""
        instructor_id = uuid.uuid4()
        payload = CourseCreate.model_validate(
            {
                "title": "Deduped",
                "add_me_as_instructor": False,
                "instructor_ids": [instructor_id, instructor_id],
            }
        )
        assert payload.instructor_ids == [instructor_id]

    @pytest.mark.parametrize(
        "payload,error_substring",
        [
            (
                {"title": "No Instructor", "add_me_as_instructor": False, "instructor_ids": []},
                "At least one instructor",
            ),
            (
                {
                    "title": "Too Many",
                    "add_me_as_instructor": False,
                    "instructor_ids": [str(uuid.uuid4()) for _ in range(MAX_INSTRUCTORS_PER_COURSE + 1)],
                },
                None,
            ),
            ({"title": "", "add_me_as_instructor": True, "instructor_ids": []}, None),
        ],
        ids=["no_instructor", "too_many_instructors", "empty_title"],
    )
    def test_invalid_payload_raises(self, payload, error_substring):
        """Invalid payload raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CourseCreate.model_validate(payload)
        if error_substring:
            errors = exc_info.value.errors()
            assert any(error_substring in str(e.get("msg", "")) for e in errors)
