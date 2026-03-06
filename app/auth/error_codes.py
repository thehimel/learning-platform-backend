"""Error codes for the auth domain."""

from enum import Enum


class AuthErrorCode(str, Enum):
    """Use these to avoid typos in auth error codes."""

    insufficient_permissions = "insufficient_permissions"
