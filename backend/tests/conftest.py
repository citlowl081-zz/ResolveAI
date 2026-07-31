"""Shared test fixtures for all backend tests.

All integration tests are self-contained: they create their own data
via the API and do not depend on seed data or test execution order.
"""

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import psycopg2
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.database.test_guard import assert_safe_test_database_url

_TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not _TEST_DATABASE_URL:
    raise pytest.UsageError(
        "TEST_DATABASE_URL is required; use the isolated ResolveAI test database"
    )
assert _TEST_DATABASE_URL is not None
_SAFE_TEST_DATABASE_URL: str = _TEST_DATABASE_URL
try:
    assert_safe_test_database_url(_SAFE_TEST_DATABASE_URL)
except RuntimeError as exc:
    raise pytest.UsageError(str(exc)) from exc

# Set safe test configuration before importing application settings. This prevents
# pytest from ever selecting a real LLM provider or the daily demo database.
os.environ["DATABASE_URL"] = _SAFE_TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = ""
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["EMBEDDING_API_KEY"] = ""

from app.config.settings import settings  # noqa: E402
from app.database.engine import create_engine  # noqa: E402
from app.main import create_app  # noqa: E402


def _truncate_test_database() -> None:
    sync_url = _SAFE_TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    with psycopg2.connect(sync_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        )
        table_names = [str(row[0]) for row in cursor.fetchall()]
        if table_names:
            quoted = ", ".join(f'"{name}"' for name in table_names)
            cursor.execute(f"TRUNCATE TABLE {quoted} CASCADE")


@pytest.fixture(scope="session", autouse=True)
def _isolate_test_database() -> Generator[None, None, None]:
    """Start and finish every pytest run with an empty, guarded test database."""
    _truncate_test_database()
    yield
    _truncate_test_database()


@pytest_asyncio.fixture(autouse=True)
async def _reset_engine() -> AsyncGenerator[None, None]:
    """Reset the global DB engine before each test to avoid event loop conflicts."""
    import app.database.session as session_mod
    if session_mod._engine is not None:
        await session_mod._engine.dispose()
    session_mod._engine = None
    session_mod._session_factory = None
    yield
    if session_mod._engine is not None:
        await session_mod._engine.dispose()
    session_mod._engine = None
    session_mod._session_factory = None


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client. Tests using this create their own data."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ── Test user fixtures (created on demand within each test) ──

async def register_and_login(
    client: AsyncClient, email: str, password: str, full_name: str,
) -> dict[str, Any]:
    """Helper: register a user and return auth headers + user info."""
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": full_name,
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": password,
    })
    data: dict[str, Any] = resp.json()["data"]
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
    }


@pytest_asyncio.fixture
async def customer_auth(async_client: AsyncClient) -> dict:
    """Create a test customer and return auth headers + user info."""
    email = f"test-cust-{uuid.uuid4().hex[:8]}@test.com"
    return await register_and_login(async_client, email, "testpass123", "Test Customer")


@pytest_asyncio.fixture
async def admin_auth(async_client: AsyncClient) -> dict:
    """Create a test admin and return auth headers + user info."""
    email = f"test-admin-{uuid.uuid4().hex[:8]}@test.com"
    # Register first — admin creation requires a pre-existing admin or we use direct DB
    # For test simplicity, register as regular then upgrade role via DB
    await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": "adminpass123", "full_name": "Test Admin",
    })
    # Direct DB role upgrade
    engine = create_engine(settings.resolved_database_url)
    async with engine.connect() as conn:
        await conn.execute(
            text("UPDATE users SET role='ADMIN' WHERE email=:email"),
            {"email": email},
        )
        await conn.commit()
    await engine.dispose()

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": email, "password": "adminpass123",
    })
    data: dict[str, Any] = resp.json()["data"]
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
    }


@pytest_asyncio.fixture
async def operator_auth(async_client: AsyncClient) -> dict:
    """Create a test operator and return auth headers + user info."""
    email = f"test-op-{uuid.uuid4().hex[:8]}@test.com"
    await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": "oppass123", "full_name": "Test Operator",
    })
    engine = create_engine(settings.resolved_database_url)
    async with engine.connect() as conn:
        await conn.execute(
            text("UPDATE users SET role='OPERATOR' WHERE email=:email"),
            {"email": email},
        )
        await conn.commit()
    await engine.dispose()

    resp = await async_client.post("/api/v1/auth/login", json={
        "email": email, "password": "oppass123",
    })
    data: dict[str, Any] = resp.json()["data"]
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
    }


@pytest_asyncio.fixture(autouse=True)  # type: ignore[type-var]
def _reset_agent_provider() -> None:
    """Reset global ModelProvider after each test to prevent cross-test leakage."""
    from app.agent.provider import set_provider
    set_provider(None)


@pytest_asyncio.fixture
async def test_product(async_client: AsyncClient, admin_auth: dict) -> dict:
    """Create a test product and return its data."""
    resp = await async_client.post("/api/v1/products", json={
        "name": f"Test Product {uuid.uuid4().hex[:6]}",
        "category": "ELECTRONICS", "price": "199.99", "stock": 50,
    }, headers=admin_auth["headers"])
    return resp.json()["data"]  # type: ignore[no-any-return]
