"""Error codes for the courses domain."""

from enum import Enum


class CourseErrorCode(str, Enum):
    invalid_instructor_ids = "invalid_instructor_ids"
    already_enrolled = "already_enrolled"
    not_enrolled = "not_enrolled"
    course_not_found = "course_not_found"
