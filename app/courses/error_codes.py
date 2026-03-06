"""Error codes for the courses domain."""

from enum import Enum


class CourseErrorCode(str, Enum):
    invalid_instructor_ids = "invalid_instructor_ids"
