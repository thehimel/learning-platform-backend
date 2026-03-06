"""Error codes for the users domain."""

from enum import Enum


class UserErrorCode(str, Enum):
    user_not_found = "user_not_found"
    cannot_delete_self = "cannot_delete_self"
