"""Vendor-neutral LLM provider abstractions.

Defines the abstract interface that all model providers must implement,
together with shared dataclasses for messages, tools, requests, and responses.
No provider-specific types (Anthropic, OpenAI, etc.) belong in this module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatMessage:
    """A single message in a chat conversation.

    Vendor-neutral representation that maps to both OpenAI and Anthropic
    message formats without coupling to either SDK.
    """

    role: str
    """One of ``"user"``, ``"assistant"``, ``"system"``, or ``"tool"``."""

    content: str
    """The text content of the message (may be empty when *tool_calls* is set)."""

    tool_calls: list[dict[str, Any]] | None = None
    """Tool calls requested by the assistant.

    Each entry is ``{"id": str, "name": str, "arguments": dict}``.
    Only meaningful when ``role == "assistant"``.
    """

    tool_call_id: str | None = None
    """The id of the tool call this message responds to.

    Only meaningful when ``role == "tool"``.
    """

    name: str | None = None
    """Optional participant name (rarely used in vendor-neutral paths)."""


@dataclass
class ToolDefinition:
    """Definition of a tool that the LLM can invoke."""

    name: str
    """Unique name for the tool (e.g. ``"get_order_status"``)."""

    description: str
    """Human-readable description shown to the model."""

    input_schema: dict[str, Any]
    """JSON Schema describing the tool's expected arguments."""


@dataclass
class ChatRequest:
    """A complete request to send to an LLM."""

    messages: list[ChatMessage]
    """Ordered conversation history, oldest first."""

    tools: list[ToolDefinition] | None = None
    """Optional tool definitions the model may call."""

    tool_choice: str | dict[str, Any] | None = None
    """Tool-selection strategy.

    - ``"auto"`` — model decides whether to call a tool (default).
    - ``"any"`` — model must call at least one tool.
    - ``"none"`` — no tools are called.
    - ``{"type": "tool", "name": "..."}`` — force a specific tool.
    """

    max_tokens: int = 4096
    """Upper bound on completion tokens."""

    temperature: float = 0.3
    """Sampling temperature (0.0–1.0)."""


@dataclass
class ChatResponse:
    """A response returned by an LLM."""

    content: str
    """Text content of the response (may be empty when tool calls exist)."""

    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    """Tool calls the model requests.

    Each entry is ``{"id": str, "name": str, "arguments": dict}``.
    """

    finish_reason: str = "stop"
    """Why the model stopped: ``"stop"``, ``"tool_calls"``, ``"length"``, etc."""

    model: str = ""
    """Identifier of the model that produced this response."""

    usage: dict[str, int] = field(default_factory=dict)
    """Token counts: ``{"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}``."""

    latency_ms: int = 0
    """Wall-clock latency of the API call in milliseconds."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Non-sensitive provider diagnostics for trace generation."""


class ModelProvider(ABC):
    """Abstract base class for LLM model providers.

    Every provider (Anthropic, OpenAI, mock, etc.) must implement both
    ``chat()`` and ``chat_structured()``.
    """

    @property
    def provider_name(self) -> str:
        """Return a non-sensitive provider identifier for traces."""
        name = type(self).__name__.removesuffix("Provider").lower()
        return name or "unknown"

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat request and return a plain-text or tool-calling response."""
        ...

    @abstractmethod
    async def chat_structured(
        self, request: ChatRequest, output_schema: dict[str, Any]
    ) -> ChatResponse:
        """Send a chat request expecting structured (JSON) output.

        The provider guarantees that ``response.content`` contains a JSON
        string matching *output_schema*.
        """
        ...
