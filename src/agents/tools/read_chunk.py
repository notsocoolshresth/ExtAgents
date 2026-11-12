"""Read chunk tool for the agentic pipeline."""

from ..base import Tool, ToolResult
from ..context import ContextManager
from ..tools import register_tool


@register_tool("read_chunk")
class ReadChunkTool:
    """Read a full chunk by its ID."""
    
    name = "read_chunk"
    description = "Read the full text of a specific chunk by ID. Args: chunk_id (int)"
    
    def __init__(self, client=None, model=None, tokenizer=None):
        self.client = client
        self.model = model
        self.tokenizer = tokenizer
    
    def execute(self, ctx: ContextManager, chunk_id: int) -> ToolResult:
        """Execute read chunk."""
        try:
            result = ctx.get_chunk(chunk_id)
            data = {
                "chunk_id": result.chunk_id,
                "text": result.text,
                "token_start": result.token_start,
                "token_end": result.token_end
            }
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))