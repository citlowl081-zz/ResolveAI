"""Manual Qwen smoke checks. This script is intentionally excluded from CI."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any

import httpx

from app.config import settings
from app.llm.factory import build_model_provider
from app.llm.openai_compatible_provider import OpenAICompatibleHTTPError
from app.llm.provider import ChatMessage, ChatRequest, ToolDefinition

_STRUCTURED_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "is_action_request": {"type": "boolean"},
    },
    "required": ["intent", "is_action_request"],
    "additionalProperties": False,
}


def _masked_base_url(value: str) -> str:
    if not value or "://" not in value:
        return "MISSING"
    scheme, remainder = value.split("://", 1)
    host, _, path = remainder.partition("/")
    prefix, dot, suffix = host.partition(".")
    masked = f"{prefix[:3]}****"
    masked_host = f"{masked}{dot}{suffix}" if dot else masked
    masked_path = "/compatible-mode/v1" if path else ""
    return f"{scheme}://{masked_host}{masked_path}"


def _report(name: str, value: object) -> None:
    sys.stdout.write(f"{name}: {value}\n")


async def _provider_checks() -> bool:
    _report("API Key", "PRESENT" if settings.llm_api_key else "MISSING")
    _report("Provider", settings.llm_provider)
    _report("Model", settings.llm_model)
    _report("Base URL", _masked_base_url(settings.llm_base_url))
    if (
        settings.llm_provider != "openai_compatible"
        or not settings.llm_api_key
        or not settings.llm_base_url
    ):
        _report("Status", "WAITING_FOR_LOCAL_SECRET")
        return False

    provider = build_model_provider(settings)
    chat_started = time.monotonic()
    chat_response = await provider.chat(
        ChatRequest(
            messages=[
                ChatMessage(
                    role="user",
                    content="请用一句话说明你是什么模型。",
                )
            ]
        )
    )
    _report("Chat success", bool(chat_response.content))
    _report("Chat status code", 200)
    _report("Chat latency_ms", int((time.monotonic() - chat_started) * 1000))

    structured = await provider.chat_structured(
        ChatRequest(
            messages=[
                ChatMessage(
                    role="user",
                    content="判断这句话是否是行动请求：我想了解退货条件。",
                )
            ],
            temperature=0.0,
        ),
        _STRUCTURED_SCHEMA,
    )
    json.loads(structured.content)
    _report("Structured output schema valid", True)
    _report(
        "Structured output fallback",
        structured.metadata.get("fallback_reason") or "NONE",
    )

    tool = ToolDefinition(
        name="get_order_status",
        description="Read-only test tool returning an order status.",
        input_schema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    )
    tool_response = await provider.chat(
        ChatRequest(
            messages=[
                ChatMessage(
                    role="user",
                    content="请使用工具查询订单 ORD-TEST-001 的状态。",
                )
            ],
            tools=[tool],
            tool_choice="auto",
            temperature=0.0,
        )
    )
    valid_tool_call = bool(
        tool_response.tool_calls
        and tool_response.tool_calls[0]["name"] == "get_order_status"
        and tool_response.tool_calls[0]["id"]
    )
    _report("Tool calling success", valid_tool_call)
    _report("Tool finish reason", tool_response.finish_reason)
    return bool(chat_response.content and valid_tool_call)


async def _agent_checks() -> None:
    api_base = os.getenv("SMOKE_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
    email = os.getenv("DEMO_CUSTOMER_EMAIL", "demo@example.com")
    password = os.getenv("DEMO_CUSTOMER_PASSWORD", "demo123456")
    async with httpx.AsyncClient(timeout=120.0) as client:
        login = await client.post(
            f"{api_base}/auth/login",
            json={"email": email, "password": password},
        )
        login.raise_for_status()
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        tickets_before = await client.get(
            f"{api_base}/after-sales/tickets",
            headers=headers,
        )
        tickets_before.raise_for_status()
        before_total = int(tickets_before.json()["data"]["total"])

        consultation = await client.post(
            f"{api_base}/agent/sessions",
            headers={
                **headers,
                "Idempotency-Key": f"smoke-policy-{uuid.uuid4()}",
            },
            json={
                "message": "我买的耳机拆封试用后不合适，还可以七天无理由退货吗？"
            },
        )
        consultation.raise_for_status()
        policy_data = consultation.json()["data"]
        _report("Agent policy consultation success", bool(policy_data.get("message")))
        _report("Agent policy citations count", len(policy_data.get("citations") or []))
        _report(
            "Agent policy proposed action",
            bool(policy_data.get("proposed_actions")),
        )
        _report(
            "Agent policy pending confirmation",
            bool(policy_data.get("proposed_actions")),
        )

        tickets_after = await client.get(
            f"{api_base}/after-sales/tickets",
            headers=headers,
        )
        tickets_after.raise_for_status()
        after_total = int(tickets_after.json()["data"]["total"])
        _report("Agent policy ticket side effect", after_total != before_total)

        action = await client.post(
            f"{api_base}/agent/sessions",
            headers={
                **headers,
                "Idempotency-Key": f"smoke-action-{uuid.uuid4()}",
            },
            json={"message": "我确认要退这个耳机，请帮我创建退款申请。"},
        )
        action.raise_for_status()
        action_data = action.json()["data"]
        _report(
            "Explicit action proposed",
            bool(action_data.get("proposed_actions")),
        )
        tickets_final = await client.get(
            f"{api_base}/after-sales/tickets",
            headers=headers,
        )
        tickets_final.raise_for_status()
        final_total = int(tickets_final.json()["data"]["total"])
        _report(
            "Explicit action pre-confirmation side effect",
            final_total != after_total,
        )


async def main() -> None:
    try:
        ready = await _provider_checks()
        if ready:
            await _agent_checks()
    except OpenAICompatibleHTTPError as exc:
        _report("Request success", False)
        _report("Status code", exc.status_code)
        _report("Error type", exc.error_type or exc.error_code or "upstream_error")
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError) as exc:
        _report("Request success", False)
        _report("Status code", getattr(exc, "status_code", "N/A"))
        _report("Error type", type(exc).__name__)


if __name__ == "__main__":
    asyncio.run(main())
