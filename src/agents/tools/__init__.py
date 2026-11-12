"""Tool registry for the agentic pipeline."""

from typing import Callable, Dict, List, Optional

from ..base import Tool, ToolResult
from ..context import ContextManager


_TOOLS: Dict[str, Callable[..., Tool]] = {}


def register_tool(name: str) -> Callable:
    """Decorator registering a tool class under `name`."""
    def decorator(cls: Callable[..., Tool]) -> Callable[..., Tool]:
        if name in _TOOLS:
            raise ValueError(f"tool {name!r} already registered")
        _TOOLS[name] = cls
        return cls
    return decorator


def get_tool(name: str) -> Callable[..., Tool]:
    """Get a tool class by name."""
    if name not in _TOOLS:
        raise ValueError(f"unknown tool {name!r}; available: {available_tools()}")
    return _TOOLS[name]


def available_tools() -> List[str]:
    """List available tool names."""
    return sorted(_TOOLS.keys())


def create_all_tools(client, model: str, tokenizer) -> Dict[str, Tool]:
    """Create instances of all registered tools."""
    tools = {}
    for name, cls in _TOOLS.items():
        tools[name] = cls(client=client, model=model, tokenizer=tokenizer)
    return tools


from . import bm25_search  # noqa: E402,F401
from . import read_chunk  # noqa: E402,F401
from . import read_range  # noqa: E402,F401
from . import extract  # noqa: E402,F401
from . import synthesize  # noqa: E402,F401