"""Provider accessor — set by AgentOrchestrator before graph execution.

All LangGraph nodes import ``get_provider()`` to access the current
``ModelProvider`` instance without coupling to the orchestrator.
"""

from app.llm.provider import ModelProvider

_provider: ModelProvider | None = None


def set_provider(provider: ModelProvider | None) -> None:
    """Set the current ModelProvider (called by orchestrator before graph run)."""
    global _provider
    _provider = provider


def get_provider() -> ModelProvider | None:
    """Get the current ModelProvider (called by nodes during graph execution)."""
    return _provider
