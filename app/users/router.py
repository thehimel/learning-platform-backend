import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_users.exceptions import UserNotExists

from app.auth.backend import current_active_user, current_admin
from app.exceptions import error_detail
from app.users.error_codes import UserErrorCode
from app.users.manager import UserManager, get_user_manager
from app.users.models import User
from app.users.schemas import UserAdminUpdate, UserRead, UserUpdate

router = APIRouter()

# Sub-router for admin-only /{id} routes — current_admin applied to all at once.
admin_router = APIRouter(dependencies=[Depends(current_admin)])


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(current_active_user)):
    return user


@router.patch("/me", response_model=UserRead)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    return await user_manager.update(user_update, current_user, safe=True)


@admin_router.get("/{id}", response_model=UserRead)
async def get_user(
    id: uuid.UUID,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        return await user_manager.get(id)
    except UserNotExists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail(UserErrorCode.user_not_found, "User not found."),
        )


@admin_router.patch("/{id}", response_model=UserRead)
async def update_user(
    id: uuid.UUID,
    user_update: UserAdminUpdate,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        user = await user_manager.get(id)
    except UserNotExists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail(UserErrorCode.user_not_found, "User not found."),
        )
    return await user_manager.update(user_update, user, safe=False)


@admin_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    id: uuid.UUID,
    requesting_user: User = Depends(current_admin),
    user_manager: UserManager = Depends(get_user_manager),
):
    if id == requesting_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_detail(UserErrorCode.cannot_delete_self, "You cannot delete your own account."),
        )
    try:
        user = await user_manager.get(id)
    except UserNotExists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail(UserErrorCode.user_not_found, "User not found."),
        )
    await user_manager.delete(user)


# Must stay at the bottom — include_router copies routes registered on admin_router at call time.
# Merged here so api/router.py only needs to import one object.
router.include_router(admin_router)
