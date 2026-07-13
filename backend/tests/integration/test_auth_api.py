"""Integration tests for auth API — all self-contained, no seed dependency."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, password: str, name: str) -> int:
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": name,
    })
    return r.status_code


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, Any] | None:
    r = await client.post("/api/v1/auth/login", json={
        "email": email, "password": password,
    })
    if r.status_code == 200:
        result: dict[str, Any] = r.json()["data"]
        return result
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_new_user(async_client: AsyncClient) -> None:
    email = f"reg-{uuid.uuid4().hex[:8]}@test.com"
    status = await _register(async_client, email, "testpass123", "Test User")
    assert status == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_then_login(async_client: AsyncClient) -> None:
    """Register → login: the user should be immediately available for login."""
    email = f"chain-{uuid.uuid4().hex[:8]}@test.com"
    reg_status = await _register(async_client, email, "testpass123", "Chain User")
    assert reg_status == 201

    result = await _login(async_client, email, "testpass123")
    assert result is not None
    assert "access_token" in result
    assert result["token_type"] == "bearer"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_duplicate(async_client: AsyncClient) -> None:
    email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
    status1 = await _register(async_client, email, "testpass123", "First")
    assert status1 == 201

    status2 = await _register(async_client, email, "otherpass", "Second")
    assert status2 == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient) -> None:
    email = f"wrongpw-{uuid.uuid4().hex[:8]}@test.com"
    await _register(async_client, email, "correct", "User")
    result = await _login(async_client, email, "wrongpassword")
    assert result is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient) -> None:
    email = f"me-{uuid.uuid4().hex[:8]}@test.com"
    await _register(async_client, email, "testpass123", "Me User")
    result = await _login(async_client, email, "testpass123")
    assert result is not None

    token = result["access_token"]
    response = await async_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["email"] == email
    assert data["data"]["role"] == "CUSTOMER"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient) -> None:
    email = f"refresh-{uuid.uuid4().hex[:8]}@test.com"
    await _register(async_client, email, "testpass123", "Refresh User")
    result = await _login(async_client, email, "testpass123")
    assert result is not None

    refresh = result["refresh_token"]
    response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_access_token_cannot_refresh(async_client: AsyncClient) -> None:
    email = f"norefresh-{uuid.uuid4().hex[:8]}@test.com"
    await _register(async_client, email, "testpass123", "NoRefresh User")
    result = await _login(async_client, email, "testpass123")
    assert result is not None

    access = result["access_token"]
    response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
