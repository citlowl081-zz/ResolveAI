"""ToolRegistry — the single source of truth for all available Agent tools.

Tools are registered once at startup.  The orchestrator queries the
registry to look up tools by name, and the LLM adapter calls
``get_contracts_for_llm()`` to build the function-calling schema.
"""

from __future__ import annotations

from app.llm.provider import ToolDefinition
from app.tools.base import BaseTool


class ToolRegistry:
    """Dict-backed registry of ``BaseTool`` instances keyed by name."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    # ── mutation ──────────────────────────────────────────────────

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.

        Raises ``ValueError`` if a tool with the same name is already
        registered (duplicate registration is a programmer error).
        """
        name = tool.contract.tool_name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")
        self._tools[name] = tool

    # ── queries ───────────────────────────────────────────────────

    def get(self, name: str) -> BaseTool | None:
        """Return the tool instance registered under *name*, or None."""
        return self._tools.get(name)

    def list_all(self) -> list[BaseTool]:
        """Return every registered tool (no guaranteed order)."""
        return list(self._tools.values())

    def get_contracts_for_llm(self) -> list[ToolDefinition]:
        """Return a list of ``ToolDefinition`` objects suitable for
        building the LLM function-calling schema.

        Only returns tools — this is the bridge between the tool layer
        and the LLM adapter.
        """
        return [
            ToolDefinition(
                name=t.contract.tool_name,
                description=t.contract.description,
                input_schema=t.contract.input_schema,
            )
            for t in self._tools.values()
        ]


# ──────────────────────────────────────────────────────────────────
# Module-level singleton (bootstrapped in definitions/__init__.py)
# ──────────────────────────────────────────────────────────────────

_default_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Return the module-level singleton registry.

    Raises ``RuntimeError`` if the registry has not been bootstrapped.
    """
    global _default_registry
    if _default_registry is None:
        raise RuntimeError("ToolRegistry has not been bootstrapped yet")
    return _default_registry


def set_registry(registry: ToolRegistry) -> None:
    """Set the module-level singleton registry (called once at startup)."""
    global _default_registry
    _default_registry = registry
