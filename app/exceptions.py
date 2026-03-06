"""Helpers for structured error responses."""

from enum import Enum
from typing import Any


def error_detail(code: Enum, message: str, **extra: Any) -> dict[str, Any]:
    """
    Build structured error detail dict for HTTPException.

    Use domain error code enums (e.g. CourseErrorCode).
    """
    return {"code": code.value, "message": message, **extra}
