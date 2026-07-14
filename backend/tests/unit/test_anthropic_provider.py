"""Unit tests for AnthropicProvider — entirely offline, no real API calls.

All tests use :mod:`unittest.mock` to monkeypatch the Anthropic SDK client
so that no network requests are made and no real API key is required.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.anthropic_provider import (
    AnthropicProvider,
    _anthropic_response_to_chat_response,
    _finish_reason_from_anthropic,
    _messages_to_anthropic,
    _msg_to_anthropic_content,
    _role_for_anthropic,
    _tools_to_anthropic,
)
from app.llm.provider import ChatMessage, ChatRequest, ChatResponse, ToolDefinition

# ---------------------------------------------------------------------------
# Helpers for building mock Anthropic SDK response objects
# ---------------------------------------------------------------------------


def _make_text_block(text: str) -> MagicMock:
    """Return a MagicMock mimicking an Anthropic text content block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(tool_id: str, name: str, input_data: dict[str, Any]) -> MagicMock:
    """Return a MagicMock mimicking an Anthropic tool_use content block."""
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


def _make_mock_anthropic_response(
    content_blocks: list[MagicMock] | None = None,
    stop_reason: str = "end_turn",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Return a MagicMock mimicking ``anthropic.types.Message``."""
    response = MagicMock()
    response.content = content_blocks or []
    response.stop_reason = stop_reason

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response.usage = usage

    return response


def _make_mock_anthropic_client(
    response: MagicMock | None = None,
) -> AsyncMock:
    """Return an AsyncMock standing in for ``anthropic.AsyncAnthropic``.

    The mock's ``messages.create`` method returns *response* (or a simple
    text-only default when none is provided).
    """
    if response is None:
        response = _make_mock_anthropic_response(
            content_blocks=[_make_text_block("Hello from Claude")],
        )

    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# Unit tests: internal conversion helpers
# ---------------------------------------------------------------------------


class TestMsgToAnthropicContent:
    """Tests for :func:`_msg_to_anthropic_content`."""

    def test_user_message_becomes_text_block(self) -> None:
        msg = ChatMessage(role="user", content="Hello")
        result = _msg_to_anthropic_content(msg)
        assert result == [{"type": "text", "text": "Hello"}]

    def test_assistant_message_becomes_text_block(self) -> None:
        msg = ChatMessage(role="assistant", content="How can I help?")
        result = _msg_to_anthropic_content(msg)
        assert result == [{"type": "text", "text": "How can I help?"}]

    def test_assistant_message_with_tool_calls(self) -> None:
        msg = ChatMessage(
            role="assistant",
            content="Let me check that.",
            tool_calls=[
                {"id": "tc_1", "name": "get_order", "arguments": {"order_id": 42}},
            ],
        )
        result = _msg_to_anthropic_content(msg)
        assert len(result) == 2
        assert result[0] == {"type": "text", "text": "Let me check that."}
        assert result[1] == {
            "type": "tool_use",
            "id": "tc_1",
            "name": "get_order",
            "input": {"order_id": 42},
        }

    def test_assistant_tool_calls_with_empty_content(self) -> None:
        msg = ChatMessage(
            role="assistant",
            content="",
            tool_calls=[
                {"id": "tc_2", "name": "search", "arguments": {"q": "status"}},
            ],
        )
        result = _msg_to_anthropic_content(msg)
        # When content is empty string, the text block is still emitted
        # because the condition checks truthiness ("" is falsy).
        assert len(result) == 1
        assert result[0]["type"] == "tool_use"

    def test_tool_message_becomes_tool_result_block(self) -> None:
        msg = ChatMessage(
            role="tool",
            content='{"status": "shipped"}',
            tool_call_id="tc_1",
        )
        result = _msg_to_anthropic_content(msg)
        assert result == [
            {
                "type": "tool_result",
                "tool_use_id": "tc_1",
                "content": '{"status": "shipped"}',
            }
        ]

    def test_tool_message_without_tool_call_id_falls_back_to_empty(self) -> None:
        msg = ChatMessage(role="tool", content="result", tool_call_id=None)
        result = _msg_to_anthropic_content(msg)
        assert result[0]["tool_use_id"] == ""


class TestRoleForAnthropic:
    """Tests for :func:`_role_for_anthropic`."""

    def test_user_role(self) -> None:
        assert _role_for_anthropic("user") == "user"

    def test_assistant_role(self) -> None:
        assert _role_for_anthropic("assistant") == "assistant"

    def test_tool_role_maps_to_user(self) -> None:
        assert _role_for_anthropic("tool") == "user"

    def test_system_role_maps_to_user(self) -> None:
        # System messages are extracted before role mapping, but
        # this is the fallback behavior if one slips through.
        assert _role_for_anthropic("system") == "user"

    def test_unknown_role_maps_to_assistant(self) -> None:
        assert _role_for_anthropic("unknown") == "assistant"


class TestMessagesToAnthropic:
    """Tests for :func:`_messages_to_anthropic`."""

    def test_system_messages_extracted_to_system_param(self) -> None:
        messages = [
            ChatMessage(role="system", content="You are helpful."),
        ]
        anthropic_msgs, system = _messages_to_anthropic(messages)
        assert system == "You are helpful."
        assert anthropic_msgs == []

    def test_multiple_system_messages_joined(self) -> None:
        messages = [
            ChatMessage(role="system", content="Rule 1."),
            ChatMessage(role="system", content="Rule 2."),
        ]
        _, system = _messages_to_anthropic(messages)
        assert system == "Rule 1.\nRule 2."

    def test_user_and_assistant_preserved(self) -> None:
        messages = [
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello"),
        ]
        anthropic_msgs, system = _messages_to_anthropic(messages)
        assert system is None
        assert len(anthropic_msgs) == 2
        assert anthropic_msgs[0]["role"] == "user"
        assert anthropic_msgs[1]["role"] == "assistant"

    def test_system_with_user_and_assistant(self) -> None:
        messages = [
            ChatMessage(role="system", content="Be concise."),
            ChatMessage(role="user", content="What is 2+2?"),
            ChatMessage(role="assistant", content="4"),
        ]
        anthropic_msgs, system = _messages_to_anthropic(messages)
        assert system == "Be concise."
        assert len(anthropic_msgs) == 2
        assert anthropic_msgs[0]["role"] == "user"
        assert anthropic_msgs[1]["role"] == "assistant"

    def test_no_system_messages_yields_none_system(self) -> None:
        messages = [ChatMessage(role="user", content="Hi")]
        _, system = _messages_to_anthropic(messages)
        assert system is None


class TestToolsToAnthropic:
    """Tests for :func:`_tools_to_anthropic`."""

    def test_single_tool_conversion(self) -> None:
        tools = [
            ToolDefinition(
                name="get_order",
                description="Get order by ID",
                input_schema={
                    "type": "object",
                    "properties": {"order_id": {"type": "integer"}},
                    "required": ["order_id"],
                },
            ),
        ]
        result = _tools_to_anthropic(tools)
        assert len(result) == 1
        assert result[0]["name"] == "get_order"
        assert result[0]["description"] == "Get order by ID"
        assert result[0]["input_schema"]["required"] == ["order_id"]

    def test_multiple_tools(self) -> None:
        tools = [
            ToolDefinition(
                name="tool_a",
                description="A",
                input_schema={"type": "object", "properties": {}},
            ),
            ToolDefinition(
                name="tool_b",
                description="B",
                input_schema={"type": "object", "properties": {}},
            ),
        ]
        result = _tools_to_anthropic(tools)
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[1]["name"] == "tool_b"

    def test_empty_tools_list(self) -> None:
        assert _tools_to_anthropic([]) == []


class TestFinishReasonFromAnthropic:
    """Tests for :func:`_finish_reason_from_anthropic`."""

    def test_end_turn_maps_to_stop(self) -> None:
        assert _finish_reason_from_anthropic("end_turn") == "stop"

    def test_tool_use_maps_to_tool_calls(self) -> None:
        assert _finish_reason_from_anthropic("tool_use") == "tool_calls"

    def test_max_tokens_maps_to_length(self) -> None:
        assert _finish_reason_from_anthropic("max_tokens") == "length"

    def test_stop_sequence_maps_to_stop(self) -> None:
        assert _finish_reason_from_anthropic("stop_sequence") == "stop"

    def test_none_maps_to_stop(self) -> None:
        assert _finish_reason_from_anthropic(None) == "stop"

    def test_unknown_reason_passed_through(self) -> None:
        assert _finish_reason_from_anthropic("custom_reason") == "custom_reason"


class TestBuildToolChoice:
    """Tests for :meth:`AnthropicProvider._build_tool_choice`."""

    def test_none_returns_none(self) -> None:
        assert AnthropicProvider._build_tool_choice(None) is None

    def test_string_none_returns_none(self) -> None:
        assert AnthropicProvider._build_tool_choice("none") is None

    def test_string_auto_returns_type_dict(self) -> None:
        assert AnthropicProvider._build_tool_choice("auto") == {"type": "auto"}

    def test_string_any_returns_type_dict(self) -> None:
        assert AnthropicProvider._build_tool_choice("any") == {"type": "any"}

    def test_dict_passed_through(self) -> None:
        choice = {"type": "tool", "name": "get_order"}
        assert AnthropicProvider._build_tool_choice(choice) is choice


# ---------------------------------------------------------------------------
# Unit tests: Anthropic response → ChatResponse conversion
# ---------------------------------------------------------------------------


class TestAnthropicResponseToChatResponse:
    """Tests for :func:`_anthropic_response_to_chat_response`."""

    def test_text_only_response(self) -> None:
        resp = _make_mock_anthropic_response(
            content_blocks=[_make_text_block("Hello!")],
            stop_reason="end_turn",
        )
        result = _anthropic_response_to_chat_response(resp, "claude-test", 150)
        assert result.content == "Hello!"
        assert result.tool_calls == []
        assert result.finish_reason == "stop"
        assert result.model == "claude-test"
        assert result.latency_ms == 150

    def test_multiple_text_blocks_joined(self) -> None:
        resp = _make_mock_anthropic_response(
            content_blocks=[
                _make_text_block("Part 1."),
                _make_text_block("Part 2."),
            ],
        )
        result = _anthropic_response_to_chat_response(resp, "m", 0)
        assert result.content == "Part 1.\nPart 2."

    def test_tool_use_blocks_parsed(self) -> None:
        resp = _make_mock_anthropic_response(
            content_blocks=[
                _make_tool_use_block("tc_1", "get_order", {"order_id": 42}),
            ],
            stop_reason="tool_use",
        )
        result = _anthropic_response_to_chat_response(resp, "m", 0)
        assert result.content == ""  # No text blocks
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0] == {
            "id": "tc_1",
            "name": "get_order",
            "arguments": {"order_id": 42},
        }
        assert result.finish_reason == "tool_calls"

    def test_mixed_text_and_tool_use(self) -> None:
        resp = _make_mock_anthropic_response(
            content_blocks=[
                _make_text_block("Let me look that up."),
                _make_tool_use_block("tc_2", "search", {"q": "status"}),
            ],
            stop_reason="tool_use",
        )
        result = _anthropic_response_to_chat_response(resp, "m", 0)
        assert result.content == "Let me look that up."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "search"

    def test_empty_content(self) -> None:
        resp = _make_mock_anthropic_response(content_blocks=[])
        result = _anthropic_response_to_chat_response(resp, "m", 0)
        assert result.content == ""
        assert result.tool_calls == []

    def test_token_usage_conversion(self) -> None:
        """Verify input_tokens/output_tokens → prompt/completion/total_tokens."""
        resp = _make_mock_anthropic_response(
            content_blocks=[_make_text_block("ok")],
            input_tokens=120,
            output_tokens=55,
        )
        result = _anthropic_response_to_chat_response(resp, "m", 0)
        assert result.usage == {
            "prompt_tokens": 120,
            "completion_tokens": 55,
            "total_tokens": 175,
        }

    def test_usage_none_handled(self) -> None:
        """When response.usage is None, usage dict stays empty."""
        resp = _make_mock_anthropic_response(
            content_blocks=[_make_text_block("ok")],
        )
        resp.usage = None
        result = _anthropic_response_to_chat_response(resp, "m", 0)
        assert result.usage == {}


class TestChatResponseNoAnthropicLeak:
    """Verify no Anthropic SDK types leak into the vendor-neutral ChatResponse."""

    @pytest.mark.asyncio
    async def test_chat_response_contains_no_anthropic_types(self) -> None:
        """Every field of ChatResponse must be plain Python / stdlib types."""
        mock_resp = _make_mock_anthropic_response(
            content_blocks=[
                _make_text_block("Hello!"),
                _make_tool_use_block("tc_x", "tool_x", {"k": "v"}),
            ],
            stop_reason="tool_use",
            input_tokens=10,
            output_tokens=5,
        )
        mock_client = _make_mock_anthropic_client(response=mock_resp)

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(
                api_key="sk-fake",
                default_model="claude-test",
            )
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
            )
            result = await provider.chat(request)

        # Assert the result is a ChatResponse (vendor-neutral type)
        assert isinstance(result, ChatResponse)

        # content must be plain str
        assert isinstance(result.content, str)

        # tool_calls must be a list of plain dicts
        assert isinstance(result.tool_calls, list)
        for tc in result.tool_calls:
            assert isinstance(tc, dict)
            assert isinstance(tc["id"], str)
            assert isinstance(tc["name"], str)
            assert isinstance(tc["arguments"], dict)

        # finish_reason must be plain str
        assert isinstance(result.finish_reason, str)

        # model must be plain str
        assert isinstance(result.model, str)

        # latency_ms must be plain int
        assert isinstance(result.latency_ms, int)

        # usage must be a dict of plain ints
        assert isinstance(result.usage, dict)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            assert key in result.usage
            assert isinstance(result.usage[key], int)

        # Sanity: nothing in result.__dict__ is a MagicMock or anthropic type
        for field_name in ("content", "finish_reason", "model", "latency_ms"):
            val = getattr(result, field_name)
            assert not isinstance(val, MagicMock), f"{field_name} is MagicMock"


# ---------------------------------------------------------------------------
# Integration-style tests: AnthropicProvider.chat() via mocked client
# ---------------------------------------------------------------------------


class TestAnthropicProviderChat:
    """End-to-end tests for :meth:`AnthropicProvider.chat` with a mocked client."""

    @pytest.mark.asyncio
    async def test_chat_sends_correct_messages_format(self) -> None:
        """ChatRequest messages are translated to Anthropic format correctly."""
        mock_resp = _make_mock_anthropic_response(
            content_blocks=[_make_text_block("The answer is 4.")],
        )
        mock_client = _make_mock_anthropic_client(response=mock_resp)

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(
                api_key="sk-fake",
                default_model="claude-sonnet",
            )
            request = ChatRequest(
                messages=[
                    ChatMessage(role="system", content="Be helpful."),
                    ChatMessage(role="user", content="What is 2+2?"),
                ],
                max_tokens=1024,
                temperature=0.5,
            )
            result = await provider.chat(request)

        # Result should be correct
        assert result.content == "The answer is 4."

        # The underlying client.messages.create should have been called once
        mock_client.messages.create.assert_called_once()

        call_kwargs = mock_client.messages.create.call_args.kwargs

        # Model passed through
        assert call_kwargs["model"] == "claude-sonnet"

        # System message extracted from messages list
        assert call_kwargs["system"] == "Be helpful."

        # Messages: only the user message remains
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"
        assert call_kwargs["messages"][0]["content"] == [{"type": "text", "text": "What is 2+2?"}]

        # max_tokens and temperature
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["temperature"] == 0.5

        # No tools by default
        assert call_kwargs["tools"] is None
        assert call_kwargs["tool_choice"] is None

    @pytest.mark.asyncio
    async def test_chat_sends_tools_when_provided(self) -> None:
        """When ChatRequest includes tools, they are sent to the API."""
        mock_client = _make_mock_anthropic_client()

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Track order #5")],
                tools=[
                    ToolDefinition(
                        name="track_order",
                        description="Track an order",
                        input_schema={
                            "type": "object",
                            "properties": {"order_id": {"type": "integer"}},
                            "required": ["order_id"],
                        },
                    ),
                ],
            )
            await provider.chat(request)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) == 1
        assert call_kwargs["tools"][0]["name"] == "track_order"
        assert call_kwargs["tools"][0]["input_schema"]["required"] == ["order_id"]

    @pytest.mark.asyncio
    async def test_chat_with_tool_choice_string(self) -> None:
        """tool_choice="any" is translated to Anthropic format."""
        mock_client = _make_mock_anthropic_client()

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
                tool_choice="any",
            )
            await provider.chat(request)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tool_choice"] == {"type": "any"}

    @pytest.mark.asyncio
    async def test_chat_with_tool_choice_none_string(self) -> None:
        """tool_choice="none" suppresses tool calls."""
        mock_client = _make_mock_anthropic_client()

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
                tool_choice="none",
            )
            await provider.chat(request)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tool_choice"] is None

    @pytest.mark.asyncio
    async def test_chat_with_tool_choice_dict(self) -> None:
        """A dict tool_choice is passed through as-is."""
        mock_client = _make_mock_anthropic_client()

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            custom_choice: dict[str, Any] = {"type": "tool", "name": "specific_tool"}
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
                tool_choice=custom_choice,
            )
            await provider.chat(request)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        # Should be the same object (passed through)
        assert call_kwargs["tool_choice"] is custom_choice

    @pytest.mark.asyncio
    async def test_latency_is_recorded(self) -> None:
        """latency_ms in the response is a positive integer."""
        mock_client = _make_mock_anthropic_client()

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
            )
            result = await provider.chat(request)

        assert result.latency_ms >= 0
        assert isinstance(result.latency_ms, int)

    @pytest.mark.asyncio
    async def test_client_is_lazy_initialized(self) -> None:
        """The client is not created until the first chat() call."""
        with patch(
            "app.llm.anthropic_provider._build_client",
        ) as mock_build:
            provider = AnthropicProvider(
                api_key="sk-fake",
                default_model="claude-x",
            )
            # Client should NOT be built yet
            mock_build.assert_not_called()

            # First call triggers build
            mock_build.return_value = _make_mock_anthropic_client()
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="Hi")]),
            )
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_is_reused_on_second_call(self) -> None:
        """The client is built only once and reused."""
        mock_client = _make_mock_anthropic_client()

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ) as mock_build:
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="A")]),
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="B")]),
            )
            # _build_client should only have been called once
            assert mock_build.call_count == 1


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify that SDK-level errors propagate correctly."""

    @pytest.mark.asyncio
    async def test_timeout_error_propagates(self) -> None:
        """When the SDK raises a timeout error, it propagates to the caller."""
        mock_client = AsyncMock()

        # Simulate an httpx/timeout error.  The anthropic SDK wraps httpx
        # errors, but the exact type depends on the SDK version.  We use a
        # generic TimeoutError, which is the common base.
        mock_client.messages.create = AsyncMock(side_effect=TimeoutError("Request timed out"))

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
            )
            with pytest.raises(TimeoutError, match="timed out"):
                await provider.chat(request)

    @pytest.mark.asyncio
    async def test_rate_limit_error_propagates(self) -> None:
        """When the SDK raises a rate-limit error, it propagates to the caller.

        This test simulates ``anthropic.RateLimitError`` by raising a generic
        exception whose message matches what the real SDK produces.  Because
        the provider does not import anthropic error types directly (to avoid
        coupling), we test that the exception is not silently swallowed.
        """
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("rate_limit_error: Too many requests")
        )

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
            )
            with pytest.raises(Exception, match="rate_limit_error"):
                await provider.chat(request)

    @pytest.mark.asyncio
    async def test_invalid_response_format_propagates(self) -> None:
        """When the SDK returns a malformed response, the error propagates.

        For example, if ``response.content`` contains blocks without a
        ``.type`` attribute, an AttributeError is raised.
        """
        malformed = MagicMock()
        malformed.content = [MagicMock(spec=[])]  # No .type attribute
        malformed.stop_reason = "end_turn"
        usage = MagicMock()
        usage.input_tokens = 0
        usage.output_tokens = 0
        malformed.usage = usage

        mock_client = _make_mock_anthropic_client(response=malformed)

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
            )
            with pytest.raises(AttributeError):
                await provider.chat(request)

    @pytest.mark.asyncio
    async def test_unexpected_api_error_propagates(self) -> None:
        """A completely unexpected error from the SDK is not swallowed."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=RuntimeError("Unexpected internal SDK error")
        )

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hi")],
            )
            with pytest.raises(RuntimeError, match="Unexpected internal SDK error"):
                await provider.chat(request)


# ---------------------------------------------------------------------------
# chat_structured tests
# ---------------------------------------------------------------------------


class TestChatStructured:
    """Tests for :meth:`AnthropicProvider.chat_structured`."""

    @pytest.mark.asyncio
    async def test_chat_structured_forces_tool_choice(self) -> None:
        """chat_structured must force tool_choice to the wrapper tool."""
        output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                "confidence": {"type": "number"},
            },
            "required": ["sentiment", "confidence"],
        }

        # Response: a tool_use for "structured_output" with the schema data
        mock_resp = _make_mock_anthropic_response(
            content_blocks=[
                _make_tool_use_block(
                    "tc_struct",
                    "structured_output",
                    {"sentiment": "positive", "confidence": 0.95},
                ),
            ],
            stop_reason="tool_use",
        )
        mock_client = _make_mock_anthropic_client(response=mock_resp)

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="I love this product!")],
            )
            result = await provider.chat_structured(request, output_schema)

        # The tool_choice MUST be forced to the wrapper tool
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tool_choice"] == {"type": "tool", "name": "structured_output"}

        # Tools must include the wrapper tool
        assert call_kwargs["tools"] is not None
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        assert "structured_output" in tool_names

        # The wrapper tool's input_schema must be the output_schema
        wrapper = next(t for t in call_kwargs["tools"] if t["name"] == "structured_output")
        assert wrapper["input_schema"] == output_schema

        # The result content must be the JSON-serialized tool-call arguments
        parsed = json.loads(result.content)
        assert parsed == {"sentiment": "positive", "confidence": 0.95}

    @pytest.mark.asyncio
    async def test_chat_structured_with_additional_tools(self) -> None:
        """When the request includes other tools, the wrapper is prepended."""
        output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        }

        mock_resp = _make_mock_anthropic_response(
            content_blocks=[
                _make_tool_use_block(
                    "tc_s", "structured_output", {"summary": "ok"},
                ),
            ],
            stop_reason="tool_use",
        )
        mock_client = _make_mock_anthropic_client(response=mock_resp)

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Summarize.")],
                tools=[
                    ToolDefinition(
                        name="lookup",
                        description="Look up info",
                        input_schema={"type": "object", "properties": {}},
                    ),
                ],
            )
            await provider.chat_structured(request, output_schema)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        # structured_output must be first, then the user's tools
        assert tool_names == ["structured_output", "lookup"]
        assert call_kwargs["tool_choice"] == {"type": "tool", "name": "structured_output"}

    @pytest.mark.asyncio
    async def test_chat_structured_passes_through_system_message(self) -> None:
        """System messages in structured requests are extracted correctly."""
        output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        }
        mock_resp = _make_mock_anthropic_response(
            content_blocks=[
                _make_tool_use_block("tc_a", "structured_output", {"answer": "x"}),
            ],
            stop_reason="tool_use",
        )
        mock_client = _make_mock_anthropic_client(response=mock_resp)

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[
                    ChatMessage(role="system", content="Answer concisely."),
                    ChatMessage(role="user", content="What is the capital?"),
                ],
            )
            await provider.chat_structured(request, output_schema)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "Answer concisely."
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_chat_structured_no_tool_calls_in_response(self) -> None:
        """Edge case: response has no tool_calls (model ignored the forced tool)."""
        output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
        }
        mock_resp = _make_mock_anthropic_response(
            content_blocks=[_make_text_block("I cannot produce structured output.")],
            stop_reason="end_turn",
        )
        mock_client = _make_mock_anthropic_client(response=mock_resp)

        with patch(
            "app.llm.anthropic_provider._build_client",
            return_value=mock_client,
        ):
            provider = AnthropicProvider(api_key="sk-fake", default_model="claude-x")
            request = ChatRequest(
                messages=[ChatMessage(role="user", content="Hello")],
            )
            result = await provider.chat_structured(request, output_schema)

        # When there are no tool_calls, content is left as the text response
        assert result.content == "I cannot produce structured output."
        assert result.tool_calls == []
        assert result.finish_reason == "stop"
