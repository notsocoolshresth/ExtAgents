"""Extract tool for the agentic pipeline."""

import json
from ..base import Tool, ToolResult
from ..context import ContextManager
from ..prompts import create_extract_prompt
from ..tools import register_tool
from ... import utils


@register_tool("extract")
class ExtractTool:
    """Extract structured information from a passage using LLM."""
    
    name = "extract"
    description = "Extract information relevant to the question from a passage. Args: passage (str), question (str), prior_evidence (str, optional)"
    
    def __init__(self, client, model: str, tokenizer):
        self.client = client
        self.model = model
        self.tokenizer = tokenizer
    
    def execute(
        self, 
        ctx: ContextManager, 
        passage: str, 
        question: str, 
        prior_evidence: str = ""
    ) -> ToolResult:
        """Execute extraction."""
        try:
            prompt = create_extract_prompt(passage, question, prior_evidence)
            messages = [
                {"role": "system", "content": "You are a helpful assistant that extracts relevant information from text."},
                {"role": "user", "content": prompt}
            ]
            
            response = utils.chat(messages)
            
            # Parse response as JSON
            try:
                parsed = json.loads(response)
                info = parsed.get("info", "")
                confidence = float(parsed.get("confidence", 0.5))
                citations = parsed.get("citations", [])
            except json.JSONDecodeError:
                # Fallback: treat entire response as info
                info = response
                confidence = 0.5
                citations = []
            
            data = {
                "info": info,
                "confidence": confidence,
                "citations": citations
            }
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))