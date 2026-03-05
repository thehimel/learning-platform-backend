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
    sql_echo: bool = False

    # Auth: password hashed at runtime for login timing-attack mitigation when user is not found.
    auth_dummy_password: str = ""

    # FastAPI Users — generate each with: openssl rand -hex 32
    auth_reset_password_token_secret: str
    auth_verification_token_secret: str

    # JWT: generate secret with `openssl rand -hex 32`
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_token_type: str = "bearer"

    # CORS: "*" allows all origins (dev only); use comma-separated list for production.
    cors_origins: str = "*"


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
