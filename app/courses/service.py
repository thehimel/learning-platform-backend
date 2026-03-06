from uuid import UUID

from decimal import Decimal

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert

from app.courses.exceptions import (
    AlreadyEnrolledError,
    CourseNotFoundError,
    InvalidInstructorIdsError,
    NotEnrolledError,
)
from app.courses.models import Course, CourseEnrollment, CourseInstructor, CourseRating
from app.courses.schemas import CourseCreate, CourseRate
from app.users.models import User, UserRole

# Eager load options for Course → instructors → user, enrollments. Reused to avoid N+1.
_COURSE_LOAD_OPTIONS = (
    selectinload(Course.instructors).selectinload(CourseInstructor.user),
    selectinload(Course.enrollments),
)


async def list_courses(session: AsyncSession) -> list[Course]:
    """List all courses with instructors and enrolled count. Returns ORM objects; CourseRead auto-transforms."""
    stmt = (
        select(Course)
        .options(*_COURSE_LOAD_OPTIONS)
        .order_by(Course.created_at.desc(), Course.id.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def create_course(
    payload: CourseCreate,
    current_user: User,
    session: AsyncSession,
) -> Course:
    """
    Create a course with one or more instructors.

    When add_me_as_instructor is True, current_user is added as an instructor.
    instructor_ids can add other instructors. At least one instructor required.

    Raises InvalidInstructorIdsError if any instructor_ids are invalid or
    do not have instructor/admin role.
    """
    instructor_ids = _resolve_instructor_ids(payload, current_user.id)
    instructors = await _validate_instructors(session, instructor_ids)

    course = Course(
        title=payload.title,
        description=payload.description,
    )
    session.add(course)
    await session.flush()

    course_instructors = [
        CourseInstructor(
            course_id=course.id,
            user_id=instructor.id,
            is_primary=(index == 0),
        )
        for index, instructor in enumerate(instructors)
    ]
    session.add_all(course_instructors)
    await session.commit()

    # Re-fetch with relationships for auto-transform via CourseRead
    stmt = select(Course).where(Course.id == course.id).options(*_COURSE_LOAD_OPTIONS)
    result = await session.execute(stmt)
    return result.scalars().one()


def _resolve_instructor_ids(payload: CourseCreate, current_user_id: UUID) -> list[UUID]:
    """Build deduplicated instructor list with creator first when add_me_as_instructor."""
    ids: list[UUID] = []
    if payload.add_me_as_instructor:
        ids.append(current_user_id)
    ids.extend(payload.instructor_ids)

    return list(dict.fromkeys(ids))


async def _validate_instructors(
    session: AsyncSession,
    instructor_ids: list[UUID],
) -> list[User]:
    """Fetch users by IDs and ensure all exist and have instructor or admin role."""
    stmt = select(User).where(
        User.id.in_(instructor_ids),
        or_(User.role == UserRole.instructor, User.role == UserRole.admin),
    )
    result = await session.execute(stmt)
    fetched = list(result.scalars().all())

    user_by_id = {user.id: user for user in fetched}
    users = [user_by_id[instructor_id] for instructor_id in instructor_ids if instructor_id in user_by_id]

    if len(users) != len(instructor_ids):
        missing = [instructor_id for instructor_id in instructor_ids if instructor_id not in user_by_id]
        raise InvalidInstructorIdsError(missing)
    return users


async def _course_exists(session: AsyncSession, course_id: int) -> bool:
    """Check if course exists. Lighter than session.get(Course) — no ORM materialization."""
    stmt = select(exists().where(Course.id == course_id))
    result = await session.execute(stmt)
    return result.scalar_one()


async def enroll_course(course_id: int, current_user: User, session: AsyncSession) -> CourseEnrollment:
    """
    Enroll current user in a course.

    Raises:
        CourseNotFoundError: if course does not exist
        AlreadyEnrolledError: if user is already enrolled
    """
    if not await _course_exists(session, course_id):
        raise CourseNotFoundError()

    enrollment = CourseEnrollment(course_id=course_id, user_id=current_user.id)
    session.add(enrollment)
    try:
        await session.commit()
        await session.refresh(enrollment)
    except IntegrityError:
        await session.rollback()
        # Unique (course_id, user_id) — already enrolled; course existence already verified
        raise AlreadyEnrolledError from None
    return enrollment


async def unenroll_course(course_id: int, current_user: User, session: AsyncSession) -> None:
    """
    Unenroll current user from a course.

    Raises:
        CourseNotFoundError: if course does not exist
        NotEnrolledError: if user is not enrolled
    """
    if not await _course_exists(session, course_id):
        raise CourseNotFoundError()

    stmt = delete(CourseEnrollment).where(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.user_id == current_user.id,
    )
    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise NotEnrolledError()
    await session.commit()


async def rate_course(
    course_id: int,
    payload: CourseRate,
    current_user: User,
    session: AsyncSession,
) -> None:
    """
    Rate a course (upsert). One rating per user per course; updates if already rated.

    Raises:
        CourseNotFoundError: if course does not exist
    """
    if not await _course_exists(session, course_id):
        raise CourseNotFoundError()

    rating_value = Decimal(str(round(payload.rating, 1)))
    stmt = (
        insert(CourseRating)
        .values(course_id=course_id, user_id=current_user.id, rating=rating_value)
        .on_conflict_do_update(
            constraint="uq_course_rating",
            set_={"rating": rating_value},
        )
    )
    await session.execute(stmt)

    # Recompute course aggregate rating
    avg_stmt = select(func.avg(CourseRating.rating)).where(CourseRating.course_id == course_id)
    result = await session.execute(avg_stmt)
    avg_rating = result.scalars().one_or_none()
    await session.execute(
        update(Course).where(Course.id == course_id).values(rating=avg_rating)
    )
    await session.commit()
