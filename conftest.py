"""Shared pytest fixtures for the test suite."""

import asyncio
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import asyncpg
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.auth.backend import current_active_user, current_admin, current_instructor
from app.auth.routes import RouteName as AuthRouteName
from app.courses.routes import RouteName as CourseRouteName
from app.database import get_db
from app.main import app
from app.users.models import User, UserRole
from app.users.routes import RouteName as UserRouteName


# Base URL for ASGI test client — host is ignored; requests go to app via ASGITransport.
TEST_CLIENT_BASE_URL = "http://test.server"

_log = logging.getLogger(__name__)


def _get_test_db_name() -> str:
    from app.config import settings

    return settings.postgres_db_test or f"{settings.postgres_db}_test"


async def _ensure_test_db() -> None:
    """Create test database if it does not exist, then run migrations."""
    from app.config import settings

    test_db = _get_test_db_name()
    conn_params = {
        "host": settings.postgres_host,
        "port": int(settings.postgres_port),
        "user": settings.postgres_user,
        "password": settings.postgres_password,
    }

    try:
        await asyncpg.connect(database=test_db, **conn_params)
        _log.info("Test database exists: %s", test_db)
    except asyncpg.InvalidCatalogNameError:
        sys_conn = await asyncpg.connect(database="template1", **conn_params)
        await sys_conn.execute(f'CREATE DATABASE "{test_db}"')
        await sys_conn.close()
        _log.info("Created test database: %s", test_db)

    _log.info("Running migrations on %s", test_db)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "POSTGRES_DB": test_db},
        cwd=Path(__file__).resolve().parent,
        check=True,
        capture_output=True,
    )


async def _drop_test_db() -> None:
    """Drop the test database after all tests (terminates connections first)."""
    from app.config import settings

    test_db = _get_test_db_name()
    conn_params = {
        "host": settings.postgres_host,
        "port": int(settings.postgres_port),
        "user": settings.postgres_user,
        "password": settings.postgres_password,
    }

    sys_conn = await asyncpg.connect(database="template1", **conn_params)
    await sys_conn.execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = $1 AND pid <> pg_backend_pid()",
        test_db,
    )
    await sys_conn.execute(f'DROP DATABASE IF EXISTS "{test_db}"')
    await sys_conn.close()
    _log.info("Dropped test database: %s", test_db)


def pytest_addoption(parser):
    parser.addoption(
        "--drop-test-db",
        action="store_true",
        default=False,
        help="Drop the test database after the test run",
    )


def pytest_sessionstart(session):
    """Create test database and run migrations before any tests."""
    asyncio.run(_ensure_test_db())


def pytest_sessionfinish(session, exitstatus):
    """Optionally drop the test database after all tests."""
    if session.config.getoption("--drop-test-db", default=False):
        asyncio.run(_drop_test_db())

@pytest.fixture
def routes():
    """API paths via app.url_path_for — app defines paths, tests stay in sync."""
    def users_by_id(user_id: uuid.UUID) -> str:
        return app.url_path_for(UserRouteName.users_get_by_id, id=user_id)

    def users_update_by_id(user_id: uuid.UUID) -> str:
        return app.url_path_for(UserRouteName.users_update_by_id, id=user_id)

    def users_delete_by_id(user_id: uuid.UUID) -> str:
        return app.url_path_for(UserRouteName.users_delete_by_id, id=user_id)

    def courses_enroll(course_id: int) -> str:
        return app.url_path_for(CourseRouteName.courses_enroll, id=course_id)

    def courses_unenroll(course_id: int) -> str:
        return app.url_path_for(CourseRouteName.courses_unenroll, id=course_id)

    def courses_rate(course_id: int) -> str:
        return app.url_path_for(CourseRouteName.courses_rate, id=course_id)

    return SimpleNamespace(
        users_me=app.url_path_for(UserRouteName.users_get_me),
        users_update_me=app.url_path_for(UserRouteName.users_update_me),
        users_by_id=users_by_id,
        users_update_by_id=users_update_by_id,
        users_delete_by_id=users_delete_by_id,
        courses_get=app.url_path_for(CourseRouteName.courses_get),
        courses_create=app.url_path_for(CourseRouteName.courses_create),
        courses_enroll=courses_enroll,
        courses_unenroll=courses_unenroll,
        courses_rate=courses_rate,
        auth_register=app.url_path_for(AuthRouteName.auth_register),
        auth_login=app.url_path_for(AuthRouteName.auth_login),
    )


def _get_test_db_url() -> str:
    """Use a separate test database to avoid affecting development data."""
    from app.config import settings

    test_db = settings.postgres_db_test or f"{settings.postgres_db}_test"
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{test_db}"
    )


@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped engine — reused across tests to avoid per-test engine creation."""
    engine = create_async_engine(
        _get_test_db_url(),
        poolclass=NullPool,
        echo=False,
    )
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture
async def db_session(test_engine):
    """
    Provide an async DB session with transaction rollback for isolation.

    Uses a separate test DB ({postgres_db}_test) to avoid affecting development data.
    NullPool + join_transaction_mode='create_savepoint' so app commits are rolled back.
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()

        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

        await transaction.rollback()


@pytest.fixture
async def test_instructor(db_session: AsyncSession) -> User:
    """Create and return an instructor user for tests."""
    from fastapi_users.password import PasswordHelper

    password_helper = PasswordHelper()
    user = User(
        id=uuid.uuid4(),
        email="instructor@test.example",
        hashed_password=password_helper.hash("TestPass1!"),
        is_active=True,
        is_verified=True,
        role=UserRole.instructor,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create and return an admin user for tests."""
    from fastapi_users.password import PasswordHelper

    password_helper = PasswordHelper()
    user = User(
        id=uuid.uuid4(),
        email="admin@test.example",
        hashed_password=password_helper.hash("TestPass1!"),
        is_active=True,
        is_verified=True,
        role=UserRole.admin,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def client_users(db_session, test_instructor):
    """HTTP client with current_active_user override for /api/users/me routes."""

    async def override_get_db():
        yield db_session

    async def override_current_active_user():
        return test_instructor

    app.dependency_overrides[get_db] = override_get_db  # type: ignore[attr-defined]
    app.dependency_overrides[current_active_user] = override_current_active_user  # type: ignore[attr-defined]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url=TEST_CLIENT_BASE_URL,
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture
async def client_admin(db_session, test_admin):
    """HTTP client with current_admin override for /api/users/{id} admin routes."""

    async def override_get_db():
        yield db_session

    async def override_current_admin():
        return test_admin

    app.dependency_overrides[get_db] = override_get_db  # type: ignore[attr-defined]
    app.dependency_overrides[current_admin] = override_current_admin  # type: ignore[attr-defined]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url=TEST_CLIENT_BASE_URL,
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture
async def client(db_session, test_instructor):
    """
    Async HTTP client with overridden get_db, current_active_user, and current_instructor.

    Uses httpx.AsyncClient so the request runs in the same event loop as fixtures,
    avoiding "attached to a different loop" errors with the async DB session.
    """

    async def override_get_db():
        yield db_session

    async def override_current_active_user():
        return test_instructor

    async def override_current_instructor():
        return test_instructor

    app.dependency_overrides[get_db] = override_get_db  # type: ignore[attr-defined]
    app.dependency_overrides[current_active_user] = override_current_active_user  # type: ignore[attr-defined]
    app.dependency_overrides[current_instructor] = override_current_instructor  # type: ignore[attr-defined]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url=TEST_CLIENT_BASE_URL,
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()  # type: ignore[attr-defined]


@pytest.fixture
async def client_e2e(db_session):
    """
    E2E HTTP client — only get_db overridden (test DB); auth uses real register/login.
    Use for end-to-end tests that exercise the full auth flow.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db  # type: ignore[attr-defined]

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url=TEST_CLIENT_BASE_URL,
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()  # type: ignore[attr-defined]


def _e2e_user(role: UserRole, password: str, email_prefix: str) -> User:
    """Create a User for E2E tests (not persisted)."""
    from fastapi_users.password import PasswordHelper

    return User(
        id=uuid.uuid4(),
        email=f"{email_prefix}-e2e-{uuid.uuid4().hex[:8]}@test.example",
        hashed_password=PasswordHelper().hash(password),
        is_active=True,
        is_verified=True,
        role=role,
    )


@pytest.fixture
async def admin_e2e(db_session, client_e2e, routes):
    """Admin user + token for E2E tests."""
    from app.tests.helpers import e2e_login

    admin = _e2e_user(UserRole.admin, "AdminPass1!", "admin")
    db_session.add(admin)
    await db_session.flush()
    token = await e2e_login(client_e2e, admin.email, "AdminPass1!", routes.auth_login)
    return admin, token


@pytest.fixture
async def admin_other_e2e(db_session, client_e2e, routes):
    """Admin user, other user, and token for E2E tests."""
    from app.tests.helpers import e2e_login

    admin = _e2e_user(UserRole.admin, "AdminPass1!", "admin")
    other = _e2e_user(UserRole.student, "OtherPass1!", "other")
    db_session.add(admin)
    db_session.add(other)
    await db_session.flush()
    token = await e2e_login(client_e2e, admin.email, "AdminPass1!", routes.auth_login)
    return admin, other, token


@pytest.fixture
async def instructor_e2e(db_session, client_e2e, routes):
    """Instructor user + token for E2E tests."""
    from app.tests.helpers import e2e_login

    instructor = _e2e_user(UserRole.instructor, "InstructorPass1!", "instructor")
    db_session.add(instructor)
    await db_session.flush()
    token = await e2e_login(client_e2e, instructor.email, "InstructorPass1!", routes.auth_login)
    return instructor, token


@pytest.fixture
async def instructor_other_e2e(db_session, client_e2e, routes):
    """Instructor user, other user, and token for E2E tests."""
    from app.tests.helpers import e2e_login

    instructor = _e2e_user(UserRole.instructor, "InstructorPass1!", "instructor")
    other = _e2e_user(UserRole.student, "OtherPass1!", "other")
    db_session.add(instructor)
    db_session.add(other)
    await db_session.flush()
    token = await e2e_login(client_e2e, instructor.email, "InstructorPass1!", routes.auth_login)
    return instructor, other, token
