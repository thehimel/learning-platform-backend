import uuid
from typing import Optional

from fastapi import Depends, Request, Response
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase

from app.config import settings
from app.logger import get_logger
from app.users.dependencies import get_user_db
from app.users.models import User

logger = get_logger(__name__)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth_reset_password_token_secret
    verification_token_secret = settings.auth_verification_token_secret

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.info("User %s registered with role '%s'.", user.id, user.role)

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ):
        logger.info("User %s logged in.", user.id)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        logger.info("User %s requested a password reset.", user.id)
        # TODO: send password reset email — see docs/config/email-setup.md

    async def on_after_reset_password(self, user: User, request: Optional[Request] = None):
        logger.info("User %s reset their password.", user.id)

    async def on_before_delete(self, user: User, request: Optional[Request] = None):
        logger.info("User %s is about to be deleted.", user.id)

    async def on_after_delete(self, user: User, request: Optional[Request] = None):
        logger.info("User %s has been deleted.", user.id)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)
