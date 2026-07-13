"""Integration tests for orders API — all self-contained, no seed dependency."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient


def _idem_key() -> str:
    return str(uuid.uuid4())


async def _create_and_pay(
    client: AsyncClient, customer: dict[str, Any], product: dict[str, Any],
) -> dict[str, Any]:
    """Helper: create an order, pay it. Returns paid order."""
    headers = customer["headers"]
    create = await client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    assert create.status_code == 201
    order = create.json()["data"]

    pay = await client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"expected_version": order["version"]},
        headers={**headers, "Idempotency-Key": _idem_key()},
    )
    assert pay.status_code == 200
    result = pay.json()["data"]
    return result  # type: ignore[no-any-return]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order(
    async_client: AsyncClient, customer_auth: dict, test_product: dict,
) -> None:
    response = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": test_product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**customer_auth["headers"], "Idempotency-Key": _idem_key()})
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "PENDING_PAYMENT"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_aggregates_duplicates(
    async_client: AsyncClient, customer_auth: dict, test_product: dict,
) -> None:
    response = await async_client.post("/api/v1/orders", json={
        "items": [
            {"product_id": test_product["id"], "quantity": 2},
            {"product_id": test_product["id"], "quantity": 3},
        ],
        "shipping_address": "Test Address",
    }, headers={**customer_auth["headers"], "Idempotency-Key": _idem_key()})
    assert response.status_code == 201
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pay_order(
    async_client: AsyncClient, customer_auth: dict, test_product: dict,
) -> None:
    await _create_and_pay(async_client, customer_auth, test_product)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_pending_payment(
    async_client: AsyncClient, customer_auth: dict, test_product: dict,
) -> None:
    headers = customer_auth["headers"]
    create = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": test_product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    order = create.json()["data"]

    cancel = await async_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        json={"expected_version": order["version"], "reason": "test"},
        headers={**headers, "Idempotency-Key": _idem_key()},
    )
    assert cancel.status_code == 200
    assert cancel.json()["data"]["status"] == "CANCELLED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cannot_cancel_paid_order(
    async_client: AsyncClient, customer_auth: dict, test_product: dict,
) -> None:
    order = await _create_and_pay(async_client, customer_auth, test_product)

    cancel = await async_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        json={"expected_version": order["version"], "reason": "test"},
        headers={**customer_auth["headers"], "Idempotency-Key": _idem_key()},
    )
    assert cancel.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ship_order(
    async_client: AsyncClient, customer_auth: dict, test_product: dict,
    operator_auth: dict,
) -> None:
    order = await _create_and_pay(async_client, customer_auth, test_product)

    ship = await async_client.post(
        f"/api/v1/orders/{order['id']}/ship",
        json={"expected_version": order["version"]},
        headers={**operator_auth["headers"], "Idempotency-Key": _idem_key()},
    )
    assert ship.status_code == 200
    assert ship.json()["data"]["status"] == "SHIPPED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_pay_idempotent(
    async_client: AsyncClient, customer_auth: dict, test_product: dict,
) -> None:
    headers = customer_auth["headers"]
    create = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": test_product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    order = create.json()["data"]
    key = _idem_key()

    pay1 = await async_client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"expected_version": order["version"]},
        headers={**headers, "Idempotency-Key": key},
    )
    assert pay1.status_code == 200

    pay2 = await async_client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"expected_version": order["version"]},
        headers={**headers, "Idempotency-Key": key},
    )
    assert pay2.status_code == 200
