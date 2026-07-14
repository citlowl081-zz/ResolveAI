"""Agent tools package.

Public API:
- ``ToolContract``, ``ToolResult``, ``BaseTool`` — base abstractions.
- ``ToolRegistry`` — registry singleton.
- ``execute_tool`` — session-scoped execution with timeout/retry.
- ``register_all`` — bootstrap helper that wires up all tools.
"""

from app.tools.base import BaseTool, ToolContract, ToolResult

# Convenience re-export: call this once at startup.
from app.tools.definitions import register_all  # noqa: F401 (re-exported)
from app.tools.executor import execute_tool
from app.tools.registry import ToolRegistry, get_registry, set_registry

__all__ = [
    "BaseTool",
    "ToolContract",
    "ToolResult",
    "ToolRegistry",
    "execute_tool",
    "get_registry",
    "set_registry",
    "register_all",
]
