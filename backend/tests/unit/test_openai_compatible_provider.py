"""Offline tests for the OpenAI-compatible chat provider."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.llm.openai_compatible_provider import OpenAICompatibleProvider
from app.llm.provider import ChatMessage, ChatRequest, ToolDefinition


def _provider(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    max_retries: int = 0,
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        api_key="test-key-not-a-secret",
        base_url="https://workspace.example/compatible-mode/v1",
        default_model="qwen-test",
        max_retries=max_retries,
        transport=httpx.MockTransport(handler),
    )


def _text_response(content: str, *, finish_reason: str = "stop") -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "model": "qwen-test",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


@pytest.mark.asyncio
async def test_chat_uses_base_url_without_duplicate_v1() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_text_response("你好"))

    response = await _provider(handler).chat(
        ChatRequest(messages=[ChatMessage(role="user", content="你好")])
    )

    assert captured["url"] == (
        "https://workspace.example/compatible-mode/v1/chat/completions"
    )
    assert captured["payload"]["model"] == "qwen-test"
    assert captured["payload"]["enable_thinking"] is False
    assert response.content == "你好"
    assert response.model == "qwen-test"
    assert response.usage["total_tokens"] == 15
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_non_qwen_model_does_not_receive_qwen_thinking_parameter() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_text_response("你好"))

    provider = OpenAICompatibleProvider(
        api_key="test-key-not-a-secret",
        base_url="https://workspace.example/compatible-mode/v1",
        default_model="other-model",
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    await provider.chat(
        ChatRequest(messages=[ChatMessage(role="user", content="你好")])
    )

    assert "enable_thinking" not in captured["payload"]


@pytest.mark.asyncio
async def test_chat_parses_and_validates_tool_calls() -> None:
    tool = ToolDefinition(
        name="get_order_status",
        description="Read an order status",
        input_schema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["tool_choice"] == "auto"
        assert payload["tools"][0]["function"]["parameters"] == tool.input_schema
        body = _text_response("", finish_reason="tool_calls")
        body["choices"][0]["message"]["tool_calls"] = [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "get_order_status",
                    "arguments": '{"order_id":"ORD-001"}',
                },
            }
        ]
        return httpx.Response(200, json=body)

    response = await _provider(handler).chat(
        ChatRequest(
            messages=[ChatMessage(role="user", content="查订单")],
            tools=[tool],
            tool_choice="auto",
        )
    )

    assert response.finish_reason == "tool_calls"
    assert response.tool_calls == [
        {
            "id": "call-1",
            "name": "get_order_status",
            "arguments": {"order_id": "ORD-001"},
        }
    ]


@pytest.mark.asyncio
async def test_chat_rejects_invalid_tool_arguments() -> None:
    tool = ToolDefinition(
        name="get_order_status",
        description="Read an order status",
        input_schema={
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = _text_response("", finish_reason="tool_calls")
        body["choices"][0]["message"]["tool_calls"] = [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "get_order_status",
                    "arguments": '{"unexpected":true}',
                },
            }
        ]
        return httpx.Response(200, json=body)

    with pytest.raises(ValueError, match="Tool arguments violate schema"):
        await _provider(handler).chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content="查订单")],
                tools=[tool],
            )
        )


@pytest.mark.asyncio
async def test_structured_output_prefers_json_schema() -> None:
    schema = {
        "type": "object",
        "properties": {"intent": {"type": "string"}},
        "required": ["intent"],
        "additionalProperties": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["response_format"] == {
            "type": "json_schema",
            "json_schema": {
                "name": "structured_output",
                "strict": True,
                "schema": schema,
            },
        }
        return httpx.Response(200, json=_text_response('{"intent":"OTHER"}'))

    response = await _provider(handler).chat_structured(
        ChatRequest(messages=[ChatMessage(role="user", content="你好")]),
        schema,
    )

    assert json.loads(response.content) == {"intent": "OTHER"}
    assert response.metadata["structured_output_failed"] is False
    assert response.metadata["fallback_used"] is False


@pytest.mark.asyncio
async def test_structured_output_falls_back_to_json_object() -> None:
    schema = {
        "type": "object",
        "properties": {"intent": {"type": "string"}},
        "required": ["intent"],
        "additionalProperties": False,
    }
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        payload = json.loads(request.content)
        if attempts == 1:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "unsupported_response_format",
                        "param": "response_format",
                    }
                },
            )
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["messages"][0]["role"] == "system"
        return httpx.Response(200, json=_text_response('{"intent":"OTHER"}'))

    response = await _provider(handler).chat_structured(
        ChatRequest(messages=[ChatMessage(role="user", content="你好")]),
        schema,
    )

    assert attempts == 2
    assert response.metadata["structured_output_failed"] is True
    assert response.metadata["fallback_used"] is True
    assert response.metadata["fallback_reason"] == "json_schema_unsupported"


@pytest.mark.asyncio
async def test_structured_output_falls_back_to_plain_json_instruction() -> None:
    schema = {
        "type": "object",
        "properties": {"intent": {"type": "string"}},
        "required": ["intent"],
        "additionalProperties": False,
    }
    payloads: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        payloads.append(payload)
        if len(payloads) < 3:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "type": "invalid_request_error",
                        "code": "unsupported_response_format",
                        "param": "response_format",
                    }
                },
            )
        return httpx.Response(200, json=_text_response('{"intent":"OTHER"}'))

    response = await _provider(handler).chat_structured(
        ChatRequest(messages=[ChatMessage(role="user", content="你好")]),
        schema,
    )

    assert len(payloads) == 3
    assert "response_format" not in payloads[2]
    assert response.metadata["fallback_reason"] == "response_format_unsupported"


@pytest.mark.asyncio
async def test_structured_output_rejects_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_text_response("not-json"))

    with pytest.raises(ValueError, match="valid structured JSON"):
        await _provider(handler).chat_structured(
            ChatRequest(messages=[ChatMessage(role="user", content="你好")]),
            {"type": "object"},
        )


@pytest.mark.asyncio
async def test_provider_retries_transient_server_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"error": {"type": "overloaded"}})
        return httpx.Response(200, json=_text_response("ok"))

    response = await _provider(handler, max_retries=1).chat(
        ChatRequest(messages=[ChatMessage(role="user", content="你好")])
    )

    assert response.content == "ok"
    assert attempts == 2


@pytest.mark.asyncio
async def test_provider_error_redacts_api_key() -> None:
    api_key = "test-sensitive-value"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            f"connection failed with {api_key}",
            request=request,
        )

    provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url="https://workspace.example/compatible-mode/v1",
        default_model="qwen-test",
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RuntimeError) as exc_info:
        await provider.chat(
            ChatRequest(messages=[ChatMessage(role="user", content="你好")])
        )

    assert api_key not in str(exc_info.value)
    assert "Authorization" not in str(exc_info.value)
