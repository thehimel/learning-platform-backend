from fastapi import APIRouter

from app.auth.backend import auth_backend, fastapi_users
from app.users.schemas import UserCreate, UserRead

router = APIRouter()

# POST /jwt/login  — returns JWT token
# POST /jwt/logout — invalidates token (client-side for JWT strategy)
router.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/jwt", tags=["Auth"])

# POST /register
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate), tags=["Auth"])
