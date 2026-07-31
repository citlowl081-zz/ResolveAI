"""Integration coverage for privacy-safe admin console reads."""

import uuid

from httpx import AsyncClient


async def test_admin_dashboard_uses_real_database_counts(
    async_client: AsyncClient, admin_auth: dict,
) -> None:
    response = await async_client.get(
        "/api/v1/admin/console/dashboard?days=7", headers=admin_auth["headers"],
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["range_days"] == 7
    assert isinstance(data["pending_tickets"], int)
    assert isinstance(data["ticket_trend"], list)


async def test_admin_console_orders_and_users_are_paginated(
    async_client: AsyncClient, admin_auth: dict,
) -> None:
    orders = await async_client.get(
        "/api/v1/admin/console/orders?page=1&page_size=5", headers=admin_auth["headers"],
    )
    users = await async_client.get(
        "/api/v1/admin/console/users?page=1&page_size=5", headers=admin_auth["headers"],
    )
    assert orders.status_code == 200
    assert users.status_code == 200
    assert orders.json()["data"]["page_size"] == 5
    assert users.json()["data"]["page_size"] == 5
    assert all("phone" not in item and "default_address" not in item for item in users.json()["data"]["items"])


async def test_admin_console_detail_not_found_is_safe(
    async_client: AsyncClient, admin_auth: dict,
) -> None:
    response = await async_client.get(
        f"/api/v1/admin/console/orders/{uuid.uuid4()}", headers=admin_auth["headers"],
    )
    assert response.status_code == 404
    assert "traceback" not in response.text.lower()


async def test_customer_cannot_access_admin_console(
    async_client: AsyncClient, customer_auth: dict,
) -> None:
    response = await async_client.get(
        "/api/v1/admin/console/system-status", headers=customer_auth["headers"],
    )
    assert response.status_code == 403


async def test_system_status_never_returns_secret_values(
    async_client: AsyncClient, admin_auth: dict,
) -> None:
    response = await async_client.get(
        "/api/v1/admin/console/system-status", headers=admin_auth["headers"],
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data["api_key_configured"], bool)
    assert isinstance(data["base_url_configured"], bool)
    assert "api_key" not in data
    assert "base_url" not in data
