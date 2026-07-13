"""Integration tests for products API — all self-contained, no seed dependency."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_products_empty_when_none(async_client: AsyncClient) -> None:
    """With no products created, list returns empty."""
    response = await async_client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"]["items"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_creates_product_then_listed(
    async_client: AsyncClient, admin_auth: dict, test_product: dict,
) -> None:
    """Product created by admin appears in list."""
    response = await async_client.get("/api/v1/products")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) >= 1
    names = [i["name"] for i in items]
    assert test_product["name"] in names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_products_paginated(
    async_client: AsyncClient, admin_auth: dict,
) -> None:
    """Pagination works correctly."""
    # Create 5 products
    for i in range(5):
        await async_client.post("/api/v1/products", json={
            "name": f"Page Product {i} {uuid.uuid4().hex[:4]}",
            "category": "HOME", "price": "10.00", "stock": 1,
        }, headers=admin_auth["headers"])

    response = await async_client.get("/api/v1/products?page=1&page_size=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["items"]) <= 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filter_by_category(
    async_client: AsyncClient, admin_auth: dict, test_product: dict,
) -> None:
    """Category filter works."""
    response = await async_client.get(f"/api/v1/products?category={test_product['category']}")
    assert response.status_code == 200
    for item in response.json()["data"]["items"]:
        assert item["category"] == test_product["category"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_admin_cannot_create_product(
    async_client: AsyncClient, customer_auth: dict,
) -> None:
    """Customer cannot create products."""
    response = await async_client.post("/api/v1/products", json={
        "name": "Bad Product", "category": "HOME", "price": "10.00", "stock": 1,
    }, headers=customer_auth["headers"])
    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_update_product_version_check(
    async_client: AsyncClient, admin_auth: dict, test_product: dict,
) -> None:
    """Version-based optimistic locking works."""
    response = await async_client.patch(
        f"/api/v1/products/{test_product['id']}",
        json={"expected_version": test_product["version"], "name": "Updated Name"},
        headers=admin_auth["headers"],
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Updated Name"
    assert response.json()["data"]["version"] == test_product["version"] + 1
