from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user, current_instructor
from app.courses.routes import RouteName
from app.courses.error_codes import CourseErrorCode
from app.courses.exceptions import (
    AlreadyEnrolledError,
    CourseNotFoundError,
    InvalidInstructorIdsError,
    NotEnrolledError,
)
from app.exceptions import error_detail
from app.courses.models import Course, CourseEnrollment
from app.courses.schemas import CourseCreate, CourseRead, CourseRate, EnrollmentRead
from app.courses.service import (
    create_course as create_course_service,
    enroll_course as enroll_course_service,
    list_courses as list_courses_service,
    rate_course as rate_course_service,
    unenroll_course as unenroll_course_service,
)
from app.database import get_db
from app.users.models import User

router = APIRouter()


@router.get("/", response_model=list[CourseRead], name=RouteName.courses_get)
async def list_courses(session: AsyncSession = Depends(get_db)) -> list[Course]:
    """List all courses. Public endpoint."""
    return await list_courses_service(session)


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED, name=RouteName.courses_create)
async def create_course(
    payload: CourseCreate,
    request: Request,
    response: Response,
    current_user: User = Depends(current_instructor),
    session: AsyncSession = Depends(get_db),
) -> Course:
    """
    Create a course with one or more instructors.

    Set add_me_as_instructor=true to add yourself as instructor. Use instructor_ids
    to add others. At least one instructor required. All instructor_ids must
    be valid users with role instructor or admin.
    """
    try:
        course = await create_course_service(payload, current_user, session)

        base_path = request.url.path.rstrip("/")
        response.headers["Location"] = f"{base_path}/{course.id}"

        return course

    except InvalidInstructorIdsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                CourseErrorCode.invalid_instructor_ids,
                str(e),
                missing_ids=[str(missing_id) for missing_id in e.missing_ids],
            ),
        )


@router.post("/{id}/enroll", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED, name=RouteName.courses_enroll)
async def enroll(
    id: int,
    request: Request,
    response: Response,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> CourseEnrollment:
    """Enroll current user in a course. Returns 201 with full enrollment resource."""
    try:
        enrollment = await enroll_course_service(id, current_user, session)
        base_path = request.url.path.removesuffix("/enroll").rstrip("/")
        response.headers["Location"] = f"{base_path}/enrollments/{enrollment.id}"
        return enrollment
    except CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail(CourseErrorCode.course_not_found, "Course not found."),
        )
    except AlreadyEnrolledError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_detail(CourseErrorCode.already_enrolled, "Already enrolled in this course."),
        )


@router.delete("/{id}/enroll", status_code=status.HTTP_204_NO_CONTENT, name=RouteName.courses_unenroll)
async def unenroll(
    id: int,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Unenroll current user from a course. Requires authentication."""
    try:
        await unenroll_course_service(id, current_user, session)
    except CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail(CourseErrorCode.course_not_found, "Course not found."),
        )
    except NotEnrolledError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_detail(CourseErrorCode.not_enrolled, "Not enrolled in this course."),
        )


@router.post("/{id}/rate", status_code=status.HTTP_204_NO_CONTENT, name=RouteName.courses_rate)
async def rate(
    id: int,
    payload: CourseRate,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Rate a course (1–5). Upserts if user already rated. Requires authentication."""
    try:
        await rate_course_service(id, payload, current_user, session)
    except CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail(CourseErrorCode.course_not_found, "Course not found."),
        )
