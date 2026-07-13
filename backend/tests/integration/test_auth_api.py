"""Integration tests for auth API."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_new_user(async_client: AsyncClient) -> None:
    email = f"testuser-{uuid.uuid4().hex[:8]}@example.com"
    response = await async_client.post("/api/v1/auth/register", json={
        "email": email, "password": "testpass123", "full_name": "Test User",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == email


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_duplicate(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/v1/auth/register", json={
        "email": "customer@test.com", "password": "testpass123", "full_name": "Dup",
    })
    assert response.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/v1/auth/login", json={
        "email": "customer@test.com", "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/v1/auth/login", json={
        "email": "customer@test.com", "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient) -> None:
    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": "customer@test.com", "password": "password123",
    })
    token = login_resp.json()["data"]["access_token"]
    response = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["email"] == "customer@test.com"
    assert data["data"]["role"] == "CUSTOMER"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient) -> None:
    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": "customer@test.com", "password": "password123",
    })
    refresh = login_resp.json()["data"]["refresh_token"]
    response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_access_token_cannot_refresh(async_client: AsyncClient) -> None:
    login_resp = await async_client.post("/api/v1/auth/login", json={
        "email": "customer@test.com", "password": "password123",
    })
    access = login_resp.json()["data"]["access_token"]
    response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
