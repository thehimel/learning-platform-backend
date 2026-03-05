import uuid

from fastapi import Depends, HTTPException, status
from fastapi_users import FastAPIUsers, models
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from app.config import settings
from app.users.manager import get_user_manager
from app.users.models import User, UserRole

bearer_transport = BearerTransport(tokenUrl="api/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(
        secret=settings.jwt_secret_key,
        lifetime_seconds=settings.jwt_access_token_expire_minutes * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Base dependency: any authenticated active user
current_active_user = fastapi_users.current_user(active=True)


# --- Role-based access control ---

def require_role(*roles: UserRole):
    """Factory that returns a dependency enforcing one of the given roles."""
    async def checker(user: User = Depends(current_active_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return user
    return checker


# Ready-to-use role dependencies — import these in route handlers
current_student = require_role(UserRole.student, UserRole.instructor, UserRole.admin)
current_instructor = require_role(UserRole.instructor, UserRole.admin)
current_admin = require_role(UserRole.admin)
