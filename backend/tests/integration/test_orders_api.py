"""Integration tests for orders API."""

import uuid

import pytest
from httpx import AsyncClient


async def _customer_headers(client: AsyncClient) -> dict:
    resp = await client.post("/api/v1/auth/login", json={
        "email": "customer@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


async def _operator_headers(client: AsyncClient) -> dict:
    resp = await client.post("/api/v1/auth/login", json={
        "email": "operator@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


def _idem_key() -> str:
    return str(uuid.uuid4())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order(async_client: AsyncClient) -> None:
    headers = await _customer_headers(async_client)
    products_resp = await async_client.get("/api/v1/products")
    product = products_resp.json()["data"]["items"][0]

    response = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "PENDING_PAYMENT"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_order_aggregates_duplicates(async_client: AsyncClient) -> None:
    headers = await _customer_headers(async_client)
    products_resp = await async_client.get("/api/v1/products")
    product = products_resp.json()["data"]["items"][0]

    response = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 2}, {"product_id": product["id"], "quantity": 3}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    assert response.status_code == 201
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pay_order(async_client: AsyncClient) -> None:
    headers = await _customer_headers(async_client)
    products_resp = await async_client.get("/api/v1/products")
    product = products_resp.json()["data"]["items"][0]

    create_resp = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    order = create_resp.json()["data"]

    pay_resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"expected_version": order["version"]},
        headers={**headers, "Idempotency-Key": _idem_key()},
    )
    assert pay_resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_pending_payment(async_client: AsyncClient) -> None:
    headers = await _customer_headers(async_client)
    products_resp = await async_client.get("/api/v1/products")
    product = products_resp.json()["data"]["items"][0]

    create_resp = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    order = create_resp.json()["data"]

    cancel_resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        json={"expected_version": order["version"], "reason": "test"},
        headers={**headers, "Idempotency-Key": _idem_key()},
    )
    assert cancel_resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cannot_cancel_paid_order(async_client: AsyncClient) -> None:
    headers = await _customer_headers(async_client)
    orders_resp = await async_client.get("/api/v1/orders", headers=headers)
    paid = next((o for o in orders_resp.json()["data"]["items"] if o["status"] == "PAID"), None)
    if paid is None:
        pytest.skip("No PAID order in seed")

    detail = await async_client.get(f"/api/v1/orders/{paid['id']}", headers=headers)
    order = detail.json()["data"]

    cancel_resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        json={"expected_version": order["version"], "reason": "test"},
        headers={**headers, "Idempotency-Key": _idem_key()},
    )
    assert cancel_resp.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ship_order(async_client: AsyncClient) -> None:
    headers = await _customer_headers(async_client)
    op_headers = await _operator_headers(async_client)
    products_resp = await async_client.get("/api/v1/products")
    product = products_resp.json()["data"]["items"][0]

    create_resp = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    order = create_resp.json()["data"]

    await async_client.post(
        f"/api/v1/orders/{order['id']}/pay",
        json={"expected_version": order["version"]},
        headers={**headers, "Idempotency-Key": _idem_key()},
    )

    detail = await async_client.get(f"/api/v1/orders/{order['id']}", headers=headers)
    updated = detail.json()["data"]

    ship_resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/ship",
        json={"expected_version": updated["version"]},
        headers={**op_headers, "Idempotency-Key": _idem_key()},
    )
    assert ship_resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_double_pay_idempotent(async_client: AsyncClient) -> None:
    headers = await _customer_headers(async_client)
    products_resp = await async_client.get("/api/v1/products")
    product = products_resp.json()["data"]["items"][0]

    create_resp = await async_client.post("/api/v1/orders", json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "shipping_address": "Test Address",
    }, headers={**headers, "Idempotency-Key": _idem_key()})
    order = create_resp.json()["data"]
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
