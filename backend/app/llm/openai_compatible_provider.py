"""OpenAI Chat Completions compatible model provider."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.llm.provider import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ModelProvider,
    ToolDefinition,
)
from app.llm.schema_validation import validate_schema_value


@dataclass
class OpenAICompatibleHTTPError(RuntimeError):
    """Safe upstream error containing no response body or credentials."""

    status_code: int
    error_type: str
    error_code: str
    error_param: str

    def __str__(self) -> str:
        return (
            "OpenAI-compatible request failed "
            f"(status={self.status_code}, type={self.error_type or 'unknown'}, "
            f"code={self.error_code or 'unknown'})"
        )

    @property
    def response_format_unsupported(self) -> bool:
        """Whether the server explicitly rejected response_format."""
        unsupported_codes = {
            "unsupported_response_format",
            "unsupported_parameter",
            "invalid_parameter",
        }
        return (
            self.status_code in {400, 422}
            and (
                self.error_param == "response_format"
                or self.error_code in unsupported_codes
            )
        )


class OpenAICompatibleProvider(ModelProvider):
    """Provider for standard OpenAI-compatible ``/chat/completions`` APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: int = 60,
        max_retries: int = 1,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout
        self._max_retries = max_retries
        self._transport = transport

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a standard OpenAI-compatible chat completion request."""
        payload = self._build_payload(request)
        return await self._send(payload, request.tools)

    async def chat_structured(
        self,
        request: ChatRequest,
        output_schema: dict[str, Any],
    ) -> ChatResponse:
        """Return schema-validated JSON using supported response-format tiers."""
        json_schema_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "structured_output",
                "strict": True,
                "schema": output_schema,
            },
        }
        try:
            response = await self._send(
                self._build_payload(request, response_format=json_schema_format),
                request.tools,
            )
            return self._validate_structured(response, output_schema)
        except OpenAICompatibleHTTPError as exc:
            if not exc.response_format_unsupported:
                raise

        instructed = self._with_json_instruction(request, output_schema)
        try:
            response = await self._send(
                self._build_payload(
                    instructed,
                    response_format={"type": "json_object"},
                ),
                instructed.tools,
            )
            response.metadata = {
                "structured_output_failed": True,
                "fallback_used": True,
                "fallback_reason": "json_schema_unsupported",
            }
            return self._validate_structured(response, output_schema)
        except OpenAICompatibleHTTPError as exc:
            if not exc.response_format_unsupported:
                raise

        response = await self._send(
            self._build_payload(instructed),
            instructed.tools,
        )
        response.metadata = {
            "structured_output_failed": True,
            "fallback_used": True,
            "fallback_reason": "response_format_unsupported",
        }
        return self._validate_structured(response, output_schema)

    def _build_payload(
        self,
        request: ChatRequest,
        *,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._default_model,
            "messages": [_message_to_openai(message) for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if self._default_model.lower().startswith("qwen"):
            # Qwen 3.7 enables thinking by default. These synchronous Agent
            # calls need the answer body, not reasoning tokens.
            payload["enable_thinking"] = False
        if request.tools:
            payload["tools"] = [_tool_to_openai(tool) for tool in request.tools]
        tool_choice = _tool_choice_to_openai(request.tool_choice)
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format is not None:
            payload["response_format"] = response_format
        return payload

    async def _send(
        self,
        payload: dict[str, Any],
        tools: list[ToolDefinition] | None,
    ) -> ChatResponse:
        endpoint = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        started = time.monotonic()
        last_error: Exception | None = None
        async with httpx.AsyncClient(
            timeout=float(self._timeout),
            transport=self._transport,
        ) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code >= 400:
                        error = _safe_http_error(response)
                        if (
                            response.status_code not in {429, 500, 502, 503, 504}
                            or attempt >= self._max_retries
                        ):
                            raise error
                        last_error = error
                    else:
                        latency_ms = int((time.monotonic() - started) * 1000)
                        return _response_to_chat(response, tools, latency_ms)
                except httpx.RequestError as exc:
                    last_error = exc
                    if attempt >= self._max_retries:
                        raise RuntimeError(
                            "OpenAI-compatible request failed (network error)"
                        ) from None
                if attempt < self._max_retries:
                    await asyncio.sleep(min(0.1 * (attempt + 1), 0.5))

        if isinstance(last_error, OpenAICompatibleHTTPError):
            raise last_error
        raise RuntimeError("OpenAI-compatible request failed")

    @staticmethod
    def _validate_structured(
        response: ChatResponse,
        output_schema: dict[str, Any],
    ) -> ChatResponse:
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise ValueError("Provider did not return valid structured JSON") from exc
        validate_schema_value(parsed, output_schema)
        response.content = json.dumps(parsed, ensure_ascii=False)
        response.metadata.setdefault("structured_output_failed", False)
        response.metadata.setdefault("fallback_used", False)
        response.metadata.setdefault("fallback_reason", None)
        return response

    @staticmethod
    def _with_json_instruction(
        request: ChatRequest,
        output_schema: dict[str, Any],
    ) -> ChatRequest:
        instruction = (
            "Return only one valid JSON object matching this JSON Schema. "
            "Do not use Markdown or add explanatory text.\n"
            f"{json.dumps(output_schema, ensure_ascii=False)}"
        )
        return ChatRequest(
            messages=[
                ChatMessage(role="system", content=instruction),
                *request.messages,
            ],
            tools=request.tools,
            tool_choice=request.tool_choice,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )


def _message_to_openai(message: ChatMessage) -> dict[str, Any]:
    result: dict[str, Any] = {
        "role": message.role,
        "content": message.content,
    }
    if message.name:
        result["name"] = message.name
    if message.role == "assistant" and message.tool_calls:
        result["tool_calls"] = [
            {
                "id": call["id"],
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                },
            }
            for call in message.tool_calls
        ]
    if message.role == "tool":
        result["tool_call_id"] = message.tool_call_id or ""
    return result


def _tool_to_openai(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def _tool_choice_to_openai(
    tool_choice: str | dict[str, Any] | None,
) -> str | dict[str, Any] | None:
    if tool_choice is None:
        return None
    if isinstance(tool_choice, str):
        return "required" if tool_choice == "any" else tool_choice
    if tool_choice.get("type") == "tool":
        return {
            "type": "function",
            "function": {"name": tool_choice.get("name", "")},
        }
    return tool_choice


def _safe_http_error(response: httpx.Response) -> OpenAICompatibleHTTPError:
    error_type = ""
    error_code = ""
    error_param = ""
    try:
        payload = response.json()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        if isinstance(error, dict):
            error_type = str(error.get("type") or "")
            error_code = str(error.get("code") or "")
            error_param = str(error.get("param") or "")
    except (ValueError, TypeError):
        pass
    return OpenAICompatibleHTTPError(
        status_code=response.status_code,
        error_type=error_type[:80],
        error_code=error_code[:80],
        error_param=error_param[:80],
    )


def _response_to_chat(
    response: httpx.Response,
    tools: list[ToolDefinition] | None,
    latency_ms: int,
) -> ChatResponse:
    try:
        payload = response.json()
        choice = payload["choices"][0]
        message = choice["message"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ValueError("Provider returned an invalid chat response") from exc

    tool_schemas = {tool.name: tool.input_schema for tool in tools or []}
    tool_calls: list[dict[str, Any]] = []
    for raw_call in message.get("tool_calls") or []:
        try:
            function = raw_call["function"]
            name = str(function["name"])
            arguments = json.loads(function["arguments"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Provider returned invalid tool arguments") from exc
        if not isinstance(arguments, dict):
            raise ValueError("Provider returned invalid tool arguments")
        schema = tool_schemas.get(name)
        if schema is not None:
            validate_schema_value(
                arguments,
                schema,
                error_prefix="Tool arguments violate schema",
            )
        tool_calls.append(
            {
                "id": str(raw_call.get("id") or ""),
                "name": name,
                "arguments": arguments,
            }
        )

    usage_payload = payload.get("usage") or {}
    usage = {
        key: int(usage_payload.get(key) or 0)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    content = message.get("content")
    return ChatResponse(
        content=content if isinstance(content, str) else "",
        tool_calls=tool_calls,
        finish_reason=str(choice.get("finish_reason") or "stop"),
        model=str(payload.get("model") or ""),
        usage=usage,
        latency_ms=latency_ms,
    )
