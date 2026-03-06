from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings

# Keyed on the client IP address.
# default_limits applies to every route in the application automatically —
# no decorator required on individual handlers.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    enabled=settings.rate_limit_enabled,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded. {exc.detail}"},
    )
