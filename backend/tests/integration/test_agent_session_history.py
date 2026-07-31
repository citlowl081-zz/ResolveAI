"""Regression tests for customer-owned persistent Agent conversations."""

import uuid

from httpx import AsyncClient


def _key() -> str:
    return str(uuid.uuid4())


async def _register(client: AsyncClient, prefix: str) -> dict[str, str]:
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"
    password = "testpass123"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": prefix,
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": email, "password": password,
    })
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_session(
    client: AsyncClient, headers: dict[str, str], message: str,
) -> tuple[str, str]:
    client_message_id = str(uuid.uuid4())
    response = await client.post(
        "/api/v1/agent/sessions",
        json={"message": message, "client_message_id": client_message_id},
        headers={**headers, "Idempotency-Key": client_message_id},
    )
    assert response.status_code == 201
    return response.json()["data"]["session_id"], client_message_id


class TestAgentSessionHistory:
    async def test_list_has_customer_safe_conversation_summary(
        self, async_client: AsyncClient,
    ) -> None:
        headers = await _register(async_client, "history-summary")
        session_id, _ = await _create_session(
            async_client, headers, "我买的是 Aurora Buds Pro，想了解售后政策",
        )

        response = await async_client.get(
            "/api/v1/agent/sessions?page=1&page_size=20", headers=headers,
        )

        assert response.status_code == 200
        item = next(
            row for row in response.json()["data"]["items"]
            if row["session_id"] == session_id
        )
        assert item["title"].startswith("我买的是 Aurora Buds Pro")
        assert item["last_message_preview"]
        assert item["message_count"] >= 2
        assert "user_id" not in item

    async def test_history_is_ordered_and_hides_internal_payloads(
        self, async_client: AsyncClient,
    ) -> None:
        headers = await _register(async_client, "history-message")
        session_id, client_message_id = await _create_session(
            async_client, headers, "退货政策是什么？",
        )

        response = await async_client.get(
            f"/api/v1/agent/sessions/{session_id}/messages?page_size=100",
            headers=headers,
        )

        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert [item["sequence_number"] for item in items] == sorted(
            item["sequence_number"] for item in items
        )
        assert {item["role"] for item in items} <= {"USER", "ASSISTANT"}
        assert items[0]["client_message_id"] == client_message_id
        for item in items:
            assert item["message_id"]
            assert item["delivery_status"] == "sent"
            assert "tool_calls" not in item
            assert "metadata" not in item
            assert isinstance(item["citations"], list)
            assert isinstance(item["proposed_actions"], list)

    async def test_other_customer_cannot_read_messages(
        self, async_client: AsyncClient,
    ) -> None:
        owner = await _register(async_client, "history-owner")
        other = await _register(async_client, "history-other")
        session_id, _ = await _create_session(async_client, owner, "你好")

        response = await async_client.get(
            f"/api/v1/agent/sessions/{session_id}/messages", headers=other,
        )

        assert response.status_code == 404

    async def test_client_message_replay_does_not_duplicate_history(
        self, async_client: AsyncClient,
    ) -> None:
        headers = await _register(async_client, "history-idempotent")
        session_id, _ = await _create_session(async_client, headers, "你好")
        client_message_id = str(uuid.uuid4())
        request_headers = {**headers, "Idempotency-Key": client_message_id}
        body = {"message": "继续聊一下", "client_message_id": client_message_id}

        first = await async_client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            json=body, headers=request_headers,
        )
        replay = await async_client.post(
            f"/api/v1/agent/sessions/{session_id}/messages",
            json=body, headers=request_headers,
        )
        history = await async_client.get(
            f"/api/v1/agent/sessions/{session_id}/messages?page_size=100",
            headers=headers,
        )

        assert first.status_code == replay.status_code == 200
        assert first.json()["data"] == replay.json()["data"]
        matching = [
            item for item in history.json()["data"]["items"]
            if item.get("client_message_id") == client_message_id
        ]
        assert len(matching) == 1
