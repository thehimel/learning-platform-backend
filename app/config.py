import os
import signal
import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: str = "5432"
    postgres_db: str = "learning-platform"
    postgres_ssl_require: bool = False  # Set true for Neon and other cloud Postgres
    postgres_db_test: str | None = None  # If unset, uses {postgres_db}_test
    sql_echo: bool = False

    # Auth: password hashed at runtime for login timing-attack mitigation when user is not found.
    # Must be non-empty — an empty string hashes near-instantaneously and defeats the timing equalisation.
    auth_dummy_password: str = "timing-equaliser-only"

    # FastAPI Users — generate each with: openssl rand -hex 32
    auth_reset_password_token_secret: str
    auth_verification_token_secret: str

    # JWT: generate secret with `openssl rand -hex 32`
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 1 day
    jwt_token_type: str = "bearer"

    # CORS: "*" allows all origins (dev only); use comma-separated list for production.
    cors_origins: str = "*"

    # When False, rate_course recomputes rating inline (for tests); when True, uses BackgroundTasks.
    rating_recompute_async: bool = True

    # When False, rate limiting is disabled (e.g. for tests).
    rate_limit_enabled: bool = True


try:
    settings = Settings()
except ValidationError as e:
    missing = [str(err["loc"][0]).upper() for err in e.errors() if err["type"] == "missing"]
    print(f"Missing: {', '.join(missing)}. Set in .env. See .env.example.", file=sys.stderr)
    try:
        os.kill(os.getppid(), signal.SIGTERM)
    except OSError:
        pass
    sys.exit(1)
