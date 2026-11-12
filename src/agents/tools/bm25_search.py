"""BM25 search tool for the agentic pipeline."""

from ..base import Tool, ToolResult
from ..context import ContextManager
from ..tools import register_tool


@register_tool("bm25_search")
class BM25SearchTool:
    """Search for relevant chunks using BM25."""
    
    name = "bm25_search"
    description = "Search for relevant text chunks using BM25 keyword matching. Args: query (str), top_k (int, default=5)"
    
    def __init__(self, client=None, model=None, tokenizer=None):
        # These are not used for BM25 search but kept for interface consistency
        self.client = client
        self.model = model
        self.tokenizer = tokenizer
    
    def execute(self, ctx: ContextManager, query: str, top_k: int = 5) -> ToolResult:
        """Execute BM25 search."""
        try:
            results = ctx.search(query, top_k)
            data = [
                {
                    "chunk_id": r.chunk_id,
                    "score": r.score,
                    "preview": r.preview
                }
                for r in results
            ]
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))