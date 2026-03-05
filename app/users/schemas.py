import uuid
from typing import Optional

from pydantic import ConfigDict, model_validator
from fastapi_users import schemas

from app.users.models import UserRole

# Fields stripped from the registration request.
_PRIVILEGED_FIELDS = ("is_active", "is_superuser", "is_verified")

# Fields stripped from the self-update request (role changes go through a dedicated admin endpoint).
_PRIVILEGED_UPDATE_FIELDS = (*_PRIVILEGED_FIELDS, "role")


def _make_schema_cleaner(*fields: str):
    """Return a json_schema_extra callback that removes the given fields."""
    def cleaner(schema: dict) -> None:
        for field in fields:
            schema.get("properties", {}).pop(field, None)
            if field in schema.get("required", []):
                schema["required"].remove(field)
    return cleaner


class UserRead(schemas.BaseUser[uuid.UUID]):
    role: UserRole


class UserCreate(schemas.BaseUserCreate):
    """
    Only email and password are accepted on registration.
    is_active, is_superuser, is_verified are stripped from the request
    and hidden from the OpenAPI schema — their values are always set
    server-side via database defaults.
    """

    model_config = ConfigDict(json_schema_extra=_make_schema_cleaner(*_PRIVILEGED_FIELDS))

    @model_validator(mode="before")
    @classmethod
    def enforce_safe_defaults(cls, values: object) -> object:
        # Pydantic v2 mode="before" may pass bytes or model instances, not just dicts.
        if isinstance(values, dict):
            for field in _PRIVILEGED_FIELDS:
                values.pop(field, None)
        return values


class UserUpdate(schemas.BaseUserUpdate):
    """
    Only password is accepted on self-update (PATCH /api/users/me).
    role changes are handled via a dedicated admin endpoint.
    is_active, is_superuser, is_verified are always managed server-side.
    """

    model_config = ConfigDict(json_schema_extra=_make_schema_cleaner(*_PRIVILEGED_UPDATE_FIELDS))

    @model_validator(mode="before")
    @classmethod
    def enforce_safe_defaults(cls, values: object) -> object:
        # Pydantic v2 mode="before" may pass bytes or model instances, not just dicts.
        if isinstance(values, dict):
            for field in _PRIVILEGED_UPDATE_FIELDS:
                values.pop(field, None)
        return values


class UserAdminUpdate(schemas.BaseUserUpdate):
    """
    All fields editable — used exclusively on PATCH /api/users/{id} (admin only).
    BaseUserUpdate already provides: password, email, is_active, is_superuser, is_verified.
    """

    role: Optional[UserRole] = None
