import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_INSTRUCTORS_PER_COURSE = 10


class CourseInstructorRead(BaseModel):
    """Minimal instructor info for course responses."""

    id: uuid.UUID
    email: str
    is_primary: bool = False

    model_config = ConfigDict(from_attributes=True, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def from_course_instructor(cls, data: Any) -> Any:
        """Auto-transform from CourseInstructor ORM (with user loaded)."""
        if hasattr(data, "user") and hasattr(data, "is_primary"):
            return {"id": data.user.id, "email": data.user.email, "is_primary": data.is_primary}
        return data


class EnrollmentRead(BaseModel):
    """Schema for enrollment resource (created on enroll)."""

    id: int
    course_id: int
    user_id: uuid.UUID
    enrolled_at: datetime

    model_config = ConfigDict(from_attributes=True, frozen=True)


class CourseRate(BaseModel):
    """Schema for rating a course (1–5, one decimal)."""

    rating: Annotated[float, Field(ge=1, le=5, description="Rating from 1 to 5 (e.g. 2.5)")]

    @model_validator(mode="after")
    def round_to_one_decimal(self) -> "CourseRate":
        self.rating = round(self.rating, 1)
        return self


class CourseCreate(BaseModel):
    """Schema for creating a course."""

    title: Annotated[str, Field(min_length=1, max_length=500)]
    description: str | None = None
    add_me_as_instructor: bool = Field(
        default=True,
        description="When true, the authenticated user is added as an instructor (primary if first).",
    )
    instructor_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=MAX_INSTRUCTORS_PER_COURSE,
        description="Other instructor user IDs. Creator is added when add_me_as_instructor=true.",
    )

    @model_validator(mode="after")
    def validate_instructors(self) -> "CourseCreate":
        if not self.add_me_as_instructor and not self.instructor_ids:
            raise ValueError(
                "At least one instructor required: set add_me_as_instructor=true or provide instructor_ids"
            )
        max_others = MAX_INSTRUCTORS_PER_COURSE - 1 if self.add_me_as_instructor else MAX_INSTRUCTORS_PER_COURSE
        if len(self.instructor_ids) > max_others:
            raise ValueError(
                f"At most {MAX_INSTRUCTORS_PER_COURSE} instructors total; provide at most {max_others} in instructor_ids"
            )
        return self

    @model_validator(mode="before")
    @classmethod
    def dedupe_instructor_ids(cls, data: object) -> object:
        if isinstance(data, dict) and "instructor_ids" in data:
            ids = data["instructor_ids"]
            if ids:
                data["instructor_ids"] = list(dict.fromkeys(ids))
        return data


class CourseRead(BaseModel):
    """Schema for course responses."""

    id: int
    title: str
    description: str | None
    published: bool
    rating: float | None = None
    created_at: datetime
    updated_at: datetime
    instructors: list[CourseInstructorRead] = Field(default_factory=list)
    enrolled_count: int = 0

    model_config = ConfigDict(from_attributes=True, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def from_course(cls, data: Any) -> Any:
        """Auto-transform from Course ORM (with instructors and enrollments loaded)."""
        if hasattr(data, "instructors") and hasattr(data, "enrollments"):
            sorted_instructors = sorted(
                data.instructors,
                key=lambda x: (not x.is_primary, x.id),
            )
            return {
                "id": data.id,
                "title": data.title,
                "description": data.description,
                "published": data.published,
                "rating": float(data.rating) if data.rating is not None else None,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "instructors": sorted_instructors,
                "enrolled_count": len(data.enrollments),
            }
        return data
