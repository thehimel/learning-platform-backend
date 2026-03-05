import enum

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    instructor = "instructor"
    admin = "admin"


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    Inherits from SQLAlchemyBaseUserTableUUID which provides:
      id, email, hashed_password, is_active, is_superuser, is_verified

    Custom fields:
      role — platform role used for RBAC (student | instructor | admin)
    """

    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole"),
        default=UserRole.student,
        server_default=UserRole.student.value,
        nullable=False,
    )
