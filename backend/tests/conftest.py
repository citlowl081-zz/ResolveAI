"""Shared test fixtures for all backend tests.

All integration tests are self-contained: they create their own data
via the API and do not depend on seed data or test execution order.
"""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config.settings import settings
from app.database.engine import create_engine
from app.main import create_app


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
