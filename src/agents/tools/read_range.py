"""Read range tool for the agentic pipeline."""

from ..base import Tool, ToolResult
from ..context import ContextManager
from ..tools import register_tool


@register_tool("read_range")
class ReadRangeTool:
    """Read an arbitrary token range from the context."""
    
    name = "read_range"
    description = "Read an arbitrary token range from the context. Args: start_token (int), end_token (int)"
    
    def __init__(self, client=None, model=None, tokenizer=None):
        self.client = client
        self.model = model
        self.tokenizer = tokenizer
    
    def execute(self, ctx: ContextManager, start_token: int, end_token: int) -> ToolResult:
        """Execute read range."""
        try:
            result = ctx.get_range(start_token, end_token)
            data = {
                "text": result.text,
                "token_start": result.token_start,
                "token_end": result.token_end
            }
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))