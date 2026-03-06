from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import router as api_router
from app.config import settings
from app.limiter import limiter, rate_limit_exceeded_handler
from app.logger import configure_logging

configure_logging()

app = FastAPI()

app.state.limiter = limiter  # type: ignore[attr-defined]
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


class RootResponse(BaseModel):
    message: str


@app.get("/", name="root", response_model=RootResponse)
def root() -> RootResponse:
    return RootResponse(message="Hello World")
