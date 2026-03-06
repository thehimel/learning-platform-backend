import ssl
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

_connect_args: dict = {}
if settings.postgres_ssl_require:
    _connect_args["ssl"] = ssl.create_default_context()

Base = declarative_base()

engine = create_async_engine(
    DATABASE_URL,
    connect_args=_connect_args if _connect_args else {},
    pool_pre_ping=True,
    echo=settings.sql_echo,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async DB session for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session
