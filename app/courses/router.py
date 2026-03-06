from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_instructor
from app.courses.error_codes import CourseErrorCode
from app.courses.exceptions import InvalidInstructorIdsError
from app.exceptions import error_detail
from app.courses.schemas import CourseCreate, CourseRead
from app.courses.service import create_course as create_course_service
from app.database import get_db
from app.users.models import User

router = APIRouter()


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    request: Request,
    response: Response,
    current_user: User = Depends(current_instructor),
    session: AsyncSession = Depends(get_db),
) -> CourseRead:
    """
    Create a course with one or more instructors.

    Set add_me_as_instructor=true to add yourself as instructor. Use instructor_ids
    to add others. At least one instructor required. All instructor_ids must
    be valid users with role instructor or admin.
    """
    try:
        course_read = await create_course_service(payload, current_user, session)

        base_path = request.url.path.rstrip("/")
        response.headers["Location"] = f"{base_path}/{course_read.id}"

        return course_read

    except InvalidInstructorIdsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                CourseErrorCode.invalid_instructor_ids,
                str(e),
                missing_ids=[str(missing_id) for missing_id in e.missing_ids],
            ),
        )
