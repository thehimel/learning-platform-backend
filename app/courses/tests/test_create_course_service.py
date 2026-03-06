"""Unit tests for the courses service layer."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.courses.exceptions import InvalidInstructorIdsError
from app.courses.schemas import CourseCreate
from app.courses.service import create_course
from app.users.models import User, UserRole


@pytest.fixture
async def second_instructor(db_session: AsyncSession) -> User:
    """Create a second instructor for multi-instructor tests."""
    from fastapi_users.password import PasswordHelper

    password_helper = PasswordHelper()
    user = User(
        id=uuid.uuid4(),
        email="instructor2@test.example",
        hashed_password=password_helper.hash("TestPass1!"),
        is_active=True,
        is_verified=True,
        role=UserRole.instructor,
    )
    db_session.add(user)
    await db_session.flush()
    return user


class TestCreateCourseService:
    """Tests for create_course service function."""

    @pytest.mark.asyncio
    async def test_create_course_adds_creator_as_primary_instructor(
        self,
        db_session: AsyncSession,
        test_instructor: User,
    ):
        """Creator is primary instructor when add_me_as_instructor=True."""
        payload = CourseCreate(
            title="Service Test Course",
            description="Testing the service",
            add_me_as_instructor=True,
            instructor_ids=[],
        )

        result = await create_course(payload, test_instructor, db_session)

        assert result.title == "Service Test Course"
        assert result.description == "Testing the service"
        assert len(result.instructors) == 1
        assert result.instructors[0].user.id == test_instructor.id
        assert result.instructors[0].user.email == test_instructor.email
        assert result.instructors[0].is_primary is True

    @pytest.mark.asyncio
    async def test_create_course_with_multiple_instructors(
        self,
        db_session: AsyncSession,
        test_instructor: User,
        second_instructor: User,
    ):
        """Multiple instructors are assigned with correct primary flag."""
        payload = CourseCreate(
            title="Multi-Instructor Course",
            add_me_as_instructor=True,
            instructor_ids=[str(second_instructor.id)],
        )

        result = await create_course(payload, test_instructor, db_session)

        assert len(result.instructors) == 2
        assert result.instructors[0].user.id == test_instructor.id
        assert result.instructors[0].is_primary is True
        assert result.instructors[1].user.id == second_instructor.id
        assert result.instructors[1].is_primary is False

    @pytest.mark.asyncio
    async def test_create_course_dedupes_instructor_ids(
        self,
        db_session: AsyncSession,
        test_instructor: User,
        second_instructor: User,
    ):
        """Duplicate instructor IDs are deduplicated."""
        payload = CourseCreate(
            title="Deduped Course",
            add_me_as_instructor=True,
            instructor_ids=[str(second_instructor.id), str(second_instructor.id)],
        )

        result = await create_course(payload, test_instructor, db_session)

        assert len(result.instructors) == 2

    @pytest.mark.asyncio
    async def test_create_course_invalid_instructor_raises(
        self,
        db_session: AsyncSession,
        test_instructor: User,
    ):
        """Invalid instructor ID raises InvalidInstructorIdsError."""
        payload = CourseCreate(
            title="Invalid Instructor Course",
            add_me_as_instructor=False,
            instructor_ids=[str(uuid.uuid4())],
        )

        with pytest.raises(InvalidInstructorIdsError) as exc_info:
            await create_course(payload, test_instructor, db_session)

        assert len(exc_info.value.missing_ids) == 1
