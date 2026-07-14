"""Anthropic model provider.

Translates the vendor-neutral types defined in :mod:`app.llm.provider`
to/from the Anthropic Messages API format.  No Anthropic SDK types leak
outside this module.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.llm.provider import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ModelProvider,
    ToolDefinition,
)

# ---------------------------------------------------------------------------
# Internal helpers — keep Anthropic SDK references confined here.
# ---------------------------------------------------------------------------


def _build_client(api_key: str, timeout: int, max_retries: int) -> Any:
    """Lazily construct an :class:`anthropic.AsyncAnthropic` client.

    The import is deferred so the module can be imported (and MockProvider
    used) even when the ``anthropic`` package is not installed.
    """
    import anthropic

    return anthropic.AsyncAnthropic(
        api_key=api_key,
        timeout=float(timeout),
        max_retries=max_retries,
    )


# ---------------------------------------------------------------------------
# ChatMessage → Anthropic message dict
# ---------------------------------------------------------------------------


def _msg_to_anthropic_content(msg: ChatMessage) -> list[dict[str, Any]]:
    """Convert a single :class:`ChatMessage` into Anthropic content blocks."""
    if msg.role == "tool":
        # Tool-result message — always maps to a tool_result block.
        return [
            {
                "type": "tool_result",
                "tool_use_id": msg.tool_call_id or "",
                "content": msg.content,
            }
        ]

    if msg.role == "assistant" and msg.tool_calls:
        blocks: list[dict[str, Any]] = []
        if msg.content:
            blocks.append({"type": "text", "text": msg.content})
        for tc in msg.tool_calls:
            blocks.append(
                {
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["arguments"],
                }
            )
        return blocks

    # Plain user / assistant / system message.
    return [{"type": "text", "text": msg.content}]


def _role_for_anthropic(role: str) -> str:
    """Anthropic only accepts ``"user"`` or ``"assistant"`` as message roles.

    ``"system"`` messages are handled via the top-level *system* parameter.
    ``"tool"`` messages become ``"user"`` messages carrying *tool_result*
    content blocks.
    """
    return "user" if role in ("user", "tool", "system") else "assistant"


def _messages_to_anthropic(
    messages: list[ChatMessage],
) -> tuple[list[dict[str, Any]], str | None]:
    """Convert our message list into (anthropic_messages, system_prompt)."""
    system_parts: list[str] = []
    anthropic_msgs: list[dict[str, Any]] = []

    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        else:
            anthropic_msgs.append(
                {
                    "role": _role_for_anthropic(msg.role),
                    "content": _msg_to_anthropic_content(msg),
                }
            )

    system = "\n".join(system_parts) if system_parts else None
    return anthropic_msgs, system


# ---------------------------------------------------------------------------
# ToolDefinition → Anthropic tool dict
# ---------------------------------------------------------------------------


def _tools_to_anthropic(
    tools: list[ToolDefinition],
) -> list[dict[str, Any]]:
    """Convert our tool definitions into Anthropic tool declarations."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in tools
    ]


# ---------------------------------------------------------------------------
# Anthropic response → ChatResponse
# ---------------------------------------------------------------------------


def _finish_reason_from_anthropic(stop_reason: str | None) -> str:
    """Map Anthropic ``stop_reason`` to a vendor-neutral finish reason."""
    if stop_reason is None:
        return "stop"
    mapping: dict[str, str] = {
        "end_turn": "stop",
        "tool_use": "tool_calls",
        "max_tokens": "length",
        "stop_sequence": "stop",
    }
    return mapping.get(stop_reason, stop_reason)


def _anthropic_response_to_chat_response(
    response: Any,  # anthropic.types.Message
    model: str,
    latency_ms: int,
) -> ChatResponse:
    """Convert an Anthropic SDK response into our vendor-neutral :class:`ChatResponse`."""
    content_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    for block in response.content:
        if block.type == "text":
            content_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                {
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                }
            )

    usage: dict[str, int] = {}
    if response.usage is not None:
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens
            + response.usage.output_tokens,
        }

    return ChatResponse(
        content="\n".join(content_parts) if content_parts else "",
        tool_calls=tool_calls,
        finish_reason=_finish_reason_from_anthropic(response.stop_reason),
        model=model,
        usage=usage,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------


class AnthropicProvider(ModelProvider):
    """Anthropic Claude provider wrapping ``anthropic.AsyncAnthropic``.

    Parameters
    ----------
    api_key:
        Anthropic API key.
    default_model:
        Model id to use when the request does not specify one
        (e.g. ``"claude-sonnet-5-20251001"``).
    timeout:
        Request timeout in seconds.  Defaults to the value of the
        ``LLM_TIMEOUT_SECONDS`` environment variable, or 60.
    max_retries:
        Maximum automatic retries.  Defaults to the value of
        ``LLM_MAX_RETRIES``, or 1.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str,
        timeout: int = 60,
        max_retries: int = 1,
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: Any = None  # anthropic.AsyncAnthropic (lazy)

    # ------------------------------------------------------------------
    # chat
    # ------------------------------------------------------------------

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat request to the Anthropic Messages API."""
        client = self._get_client()

        anthropic_msgs, system = _messages_to_anthropic(request.messages)
        tools = _tools_to_anthropic(request.tools) if request.tools else None
        tool_choice = self._build_tool_choice(request.tool_choice)

        t0 = time.monotonic()
        response = await client.messages.create(
            model=self._default_model,
            messages=anthropic_msgs,
            system=system,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            tools=tools,
            tool_choice=tool_choice,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        return _anthropic_response_to_chat_response(
            response, self._default_model, elapsed_ms
        )

    # ------------------------------------------------------------------
    # chat_structured
    # ------------------------------------------------------------------

    async def chat_structured(
        self, request: ChatRequest, output_schema: dict[str, Any]
    ) -> ChatResponse:
        """Force the model to emit JSON matching *output_schema*.

        Implementation: wraps *output_schema* inside a synthetic
        ``"structured_output"`` tool and sets ``tool_choice`` to force
        that tool.  The resulting tool-call arguments are serialized as
        JSON and placed in ``response.content``.
        """
        client = self._get_client()

        wrapper_tool = ToolDefinition(
            name="structured_output",
            description="Produce the requested structured output.",
            input_schema=output_schema,
        )

        all_tools: list[ToolDefinition] = [wrapper_tool]
        if request.tools:
            all_tools = [wrapper_tool] + list(request.tools)

        anthropic_msgs, system = _messages_to_anthropic(request.messages)
        tools = _tools_to_anthropic(all_tools)
        tool_choice: dict[str, Any] = {"type": "tool", "name": "structured_output"}

        t0 = time.monotonic()
        response = await client.messages.create(
            model=self._default_model,
            messages=anthropic_msgs,
            system=system,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            tools=tools,
            tool_choice=tool_choice,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        result = _anthropic_response_to_chat_response(
            response, self._default_model, elapsed_ms
        )

        # When tool_choice forces a tool call the response only contains
        # tool_use blocks — no text.  Extract the structured data and
        # place it in content so callers get a uniform experience.
        if result.tool_calls:
            result.content = json.dumps(result.tool_calls[0]["arguments"])

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return the lazy-constructed AsyncAnthropic client."""
        if self._client is None:
            self._client = _build_client(
                self._api_key, self._timeout, self._max_retries
            )
        return self._client

    @staticmethod
    def _build_tool_choice(
        tool_choice: str | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Normalize our vendor-neutral *tool_choice* to the Anthropic shape."""
        if tool_choice is None:
            return None
        if isinstance(tool_choice, dict):
            return tool_choice
        # string form: "auto", "any", "none"
        if tool_choice == "none":
            return None
        return {"type": tool_choice}
