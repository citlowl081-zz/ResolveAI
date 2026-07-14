"""Mock LLM provider for testing without real API calls.

Returns pre-programmed :class:`ChatResponse` objects in FIFO order and
records every request so tests can assert what was sent to the model.
"""

from __future__ import annotations

from typing import Any

from app.llm.provider import ChatRequest, ChatResponse, ModelProvider


class MockProvider(ModelProvider):
    """Model provider that returns pre-programmed responses.

    Accepts an optional list of :class:`ChatResponse` objects.  Each call
    to :meth:`chat` or :meth:`chat_structured` pops the next response from
    that list.  When the list is exhausted a generic default response is
    returned.

    All requests are appended to :attr:`call_history` for test assertions.

    Parameters
    ----------
    responses:
        Pre-programmed responses to return in FIFO order.
    """

    def __init__(self, responses: list[ChatResponse] | None = None) -> None:
        self._responses: list[ChatResponse] = list(responses) if responses else []
        self.call_history: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Record *request* and return the next programmed response (or a default)."""
        self.call_history.append(request)
        if self._responses:
            return self._responses.pop(0)
        return ChatResponse(
            content="Mock response",
            finish_reason="stop",
            model="mock",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            latency_ms=0,
        )

    async def chat_structured(
        self, request: ChatRequest, output_schema: dict[str, Any]
    ) -> ChatResponse:
        """Record *request* and return the next programmed response (or a default JSON)."""
        self.call_history.append(request)
        if self._responses:
            return self._responses.pop(0)
        return ChatResponse(
            content='{"message": "Mock structured response"}',
            finish_reason="stop",
            model="mock",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            latency_ms=0,
        )
