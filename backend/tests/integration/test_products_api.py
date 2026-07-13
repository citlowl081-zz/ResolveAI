"""Integration tests for products API."""

import pytest
from httpx import AsyncClient


async def _admin_headers(client: AsyncClient) -> dict:
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_products(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_products_paginated(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/products?page=1&page_size=3")
    assert response.status_code == 200
    assert len(response.json()["data"]["items"]) <= 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filter_by_category(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/products?category=ELECTRONICS")
    assert response.status_code == 200
    for item in response.json()["data"]["items"]:
        assert item["category"] == "ELECTRONICS"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_create_product(async_client: AsyncClient) -> None:
    headers = await _admin_headers(async_client)
    response = await async_client.post("/api/v1/products", json={
        "name": "Integration Test Product", "category": "HOME", "price": "99.99", "stock": 10,
    }, headers=headers)
    assert response.status_code == 201


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_admin_cannot_create_product(async_client: AsyncClient) -> None:
    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "customer@test.com", "password": "password123",
    })
    token = resp.json()["data"]["access_token"]
    response = await async_client.post("/api/v1/products", json={
        "name": "Bad", "category": "HOME", "price": "10.00", "stock": 1,
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
