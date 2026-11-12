"""Synthesize tool for the agentic pipeline."""

import json
from ..base import Tool, ToolResult
from ..context import ContextManager
from ..prompts import create_synthesize_prompt
from ..tools import register_tool
from ... import utils


@register_tool("synthesize")
class SynthesizeTool:
    """Synthesize final answer from collected evidence."""
    
    name = "synthesize"
    description = "Combine all collected evidence into a final answer. Args: evidence (list of dicts with info, confidence, citations), question (str)"
    
    def __init__(self, client, model: str, tokenizer):
        self.client = client
        self.model = model
        self.tokenizer = tokenizer
    
    def execute(
        self, 
        ctx: ContextManager, 
        evidence: list, 
        question: str
    ) -> ToolResult:
        """Execute synthesis."""
        try:
            # Format evidence for prompt
            evidence_str = self._format_evidence(evidence)
            
            prompt = create_synthesize_prompt(evidence_str, question)
            messages = [
                {"role": "system", "content": "You are a helpful assistant that synthesizes answers from evidence."},
                {"role": "user", "content": prompt}
            ]
            
            response = utils.chat(messages)
            
            # Parse response as JSON
            try:
                parsed = json.loads(response)
                answer = parsed.get("answer", "")
                confidence = float(parsed.get("confidence", 0.5))
                citations = parsed.get("citations", [])
            except json.JSONDecodeError:
                # Fallback: treat entire response as answer
                answer = response
                confidence = 0.5
                citations = []
            
            data = {
                "answer": answer,
                "confidence": confidence,
                "citations": citations
            }
            return ToolResult(success=True, data=data)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
    
    def _format_evidence(self, evidence: list) -> str:
        """Format evidence list into a string for the prompt."""
        if not evidence:
            return "No evidence collected."
        
        lines = []
        for i, e in enumerate(evidence):
            info = e.get("info", "") if isinstance(e, dict) else str(e)
            confidence = e.get("confidence", 0) if isinstance(e, dict) else 0
            lines.append(f"Evidence {i+1} (confidence: {confidence:.2f}):\n{info}")
        return "\n\n".join(lines)