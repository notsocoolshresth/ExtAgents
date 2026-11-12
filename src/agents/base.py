"""Base classes and protocols for the agentic pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None


class Tool(Protocol):
    """Protocol for agent tools."""
    name: str
    description: str
    
    def execute(self, ctx: "ContextManager", **kwargs) -> ToolResult:
        """Execute the tool with the given context manager and arguments."""
        ...


class ContextManager:
    """Manages the full context text, chunking, and search index.
    
    This is a forward declaration for type hints. The actual implementation
    is in context.py.
    """
    pass


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, max_steps: int = 8):
        self.max_steps = max_steps
        self.tools: Dict[str, Tool] = {}
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the agent."""
        self.tools[tool.name] = tool
    
    @abstractmethod
    def run(self, question: str, ctx: ContextManager) -> str:
        """Run the agent on a question with the given context.
        
        Returns:
            The final answer string.
        """
        ...
    
    def _format_tool_descriptions(self) -> str:
        """Format tool descriptions for the system prompt."""
        lines = []
        for tool in self.tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)


@dataclass
class Action:
    """Represents an action the agent wants to take."""
    tool: str
    args: Dict[str, Any]
    thought: str = ""