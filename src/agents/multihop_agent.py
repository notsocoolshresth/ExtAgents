"""Multihop QA agent implementation."""

import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple

from .base import BaseAgent, Tool, ToolResult, Action
from .context import ContextManager
from .prompts import create_agent_prompt, create_extract_prompt, create_synthesize_prompt
from .tools import create_all_tools, available_tools
from .. import utils
from .. import prompt as prompt_module
from . import register


logger = logging.getLogger(__name__)


class MultihopAgent(BaseAgent):
    """ReAct-style agent for multihop QA."""
    
    def __init__(
        self, 
        client, 
        model: str, 
        tokenizer, 
        max_steps: int = 8,
        log_file: Optional[str] = None
    ):
        super().__init__(max_steps)
        self.client = client
        self.model = model
        self.tokenizer = tokenizer
        self.log_file = log_file
        
        # Create all tools
        self.tools = create_all_tools(client, model, tokenizer)
        
        # Build system prompt
        tool_descriptions = self._format_tool_descriptions()
        self.system_prompt = create_agent_prompt(tool_descriptions)
    
    def _log(self, msg: str) -> None:
        """Log message to file and stdout."""
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(f"{msg}\n")
        print(msg)
    
    def run(self, question: str, ctx: ContextManager) -> str:
        """Run the agent on a question with the given context."""
        self._log(f"[Agent] Starting question: {question[:100]}...")
        
        evidence = []
        trajectory = []
        
        for step in range(self.max_steps):
            self._log(f"[Agent] Step {step + 1}/{self.max_steps}")
            
            # Decide next action
            action = self._decide_action(question, evidence, trajectory)
            self._log(f"[Agent] Thought: {action.thought}")
            self._log(f"[Agent] Action: {action.tool}({action.args})")
            
            # Execute tool
            if action.tool not in self.tools:
                error_msg = f"Unknown tool: {action.tool}"
                self._log(f"[Agent] Error: {error_msg}")
                trajectory.append({
                    "step": step,
                    "action": action,
                    "result": ToolResult(success=False, data=None, error=error_msg)
                })
                continue
            
            tool = self.tools[action.tool]
            result = tool.execute(ctx, **action.args)
            
            self._log(f"[Agent] Result: success={result.success}, error={result.error}")
            if result.success:
                self._log(f"[Agent] Data: {str(result.data)[:200]}...")
            
            trajectory.append({
                "step": step,
                "action": action,
                "result": result
            })
            
            # Update evidence if extraction
            if action.tool == "extract" and result.success:
                evidence.append(result.data)
                self._log(f"[Agent] Added evidence (total: {len(evidence)})")
            
            # Check termination
            if action.tool == "synthesize" and result.success:
                answer = result.data.get("answer", "NO ANSWER")
                self._log(f"[Agent] Final answer: {answer}")
                return answer
            
            if self._should_terminate(question, evidence, trajectory):
                # Force synthesis
                self._log("[Agent] Forcing synthesis")
                synthesize_tool = self.tools["synthesize"]
                synth_result = synthesize_tool.execute(ctx, evidence=evidence, question=question)
                if synth_result.success:
                    return synth_result.data.get("answer", "NO ANSWER")
                return "NO ANSWER"
        
        # Max steps reached, force synthesis
        self._log("[Agent] Max steps reached, forcing synthesis")
        synthesize_tool = self.tools["synthesize"]
        synth_result = synthesize_tool.execute(ctx, evidence=evidence, question=question)
        if synth_result.success:
            return synth_result.data.get("answer", "NO ANSWER")
        return "NO ANSWER"
    
    def _decide_action(
        self, 
        question: str, 
        evidence: List[Dict], 
        trajectory: List[Dict]
    ) -> Action:
        """Use LLM to decide the next action."""
        # Build context from trajectory
        context_parts = [self.system_prompt, f"\nQuestion: {question}\n"]
        
        if evidence:
            evidence_str = "\n\n".join([
                f"Evidence {i+1}: {e.get('info', '')}" 
                for i, e in enumerate(evidence)
            ])
            context_parts.append(f"\nCollected evidence:\n{evidence_str}\n")
        
        if trajectory:
            context_parts.append("Previous steps:")
            for t in trajectory:
                action = t["action"]
                result = t["result"]
                context_parts.append(f"THOUGHT: {action.thought}")
                context_parts.append(f"ACTION: {action.tool}({json.dumps(action.args)})")
                if result.success:
                    context_parts.append(f"RESULT: {json.dumps(result.data)[:500]}")
                else:
                    context_parts.append(f"ERROR: {result.error}")
        
        context_parts.append("\nTHOUGHT:")
        
        prompt = "".join(context_parts)
        
        messages = [
            {"role": "system", "content": "You are a multihop QA agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = utils.chat(messages)
        
        # Parse response
        return self._parse_action(response)
    
    def _parse_action(self, response: str) -> Action:
        """Parse the LLM response into an Action."""
        thought = ""
        tool_name = ""
        args = {}
        
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("THOUGHT:"):
                thought = line[8:].strip()
            elif line.startswith("ACTION:"):
                action_str = line[7:].strip()
                # Parse tool_name(args)
                if "(" in action_str and ")" in action_str:
                    tool_name = action_str[:action_str.index("(")].strip()
                    args_str = action_str[action_str.index("(")+1:action_str.rindex(")")]
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        # Try to parse as key=value pairs
                        args = self._parse_kv_args(args_str)
        
        if not tool_name:
            # Default to search if parsing fails
            tool_name = "bm25_search"
            args = {"query": response[:100], "top_k": 5}
            thought = "Parsing failed, defaulting to search"
        
        return Action(tool=tool_name, args=args, thought=thought)
    
    def _parse_kv_args(self, args_str: str) -> Dict:
        """Parse key=value arguments."""
        args = {}
        # Simple parsing for key=value, key="value"
        import re
        pairs = re.findall(r'(\w+)\s*=\s*([^,]+)(?:,|$)', args_str)
        for key, value in pairs:
            value = value.strip().strip('"\'')
            # Try to convert to int/float
            try:
                if '.' in value:
                    args[key] = float(value)
                else:
                    args[key] = int(value)
            except ValueError:
                args[key] = value
        return args
    
    def _should_terminate(
        self, 
        question: str, 
        evidence: List[Dict], 
        trajectory: List[Dict]
    ) -> bool:
        """Check if the agent should terminate and synthesize."""
        # Terminate if we have high-confidence evidence
        if evidence:
            max_confidence = max(e.get("confidence", 0) for e in evidence)
            if max_confidence > 0.8:
                return True
        
        # Terminate if last few steps were extract with low new info
        if len(trajectory) >= 3:
            recent_extracts = [
                t for t in trajectory[-3:] 
                if t["action"].tool == "extract" and t["result"].success
            ]
            if len(recent_extracts) >= 2:
                # Check if new info is repetitive
                infos = [t["result"].data.get("info", "") for t in recent_extracts]
                if any("NO INFORMATION" in info.upper() for info in infos):
                    return True
        
        return False


def run_agentic_pipeline(
    examples,
    tokenizer,
    task: str,
    chunk_length: int,
    input_length: int,
    output_dir,
    max_workers: int = 1,
    context_length: int = 128000,
    log_dir=None
):
    """Drop-in replacement for pipeline.run_pipeline() for the multihop agent.
    
    Only supports task='rag' for now.
    """
    from pathlib import Path
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    if task != "rag":
        raise ValueError("Multihop agent only supports task='rag'")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_output_path = output_dir / "final_preds.jsonl"
    
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
    else:
        log_dir = output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
    
    final_preds = []
    processed_ids = set()
    
    if final_output_path.exists():
        final_preds = list(utils.iter_jsonl(final_output_path))
        for pred in final_preds:
            processed_ids.add(pred["id"])
        if processed_ids:
            print(f"Found {len(processed_ids)} already processed examples")
    
    start_idx = 0
    stop_idx = len(examples)
    
    start_time = time.time()
    map_time = 0.0
    reduce_time = 0.0
    
    lock = threading.Lock()
    
    def process_result(result):
        nonlocal map_time, reduce_time
        if result is not None:
            id, final_pred, example_map_time, example_reduce_time = result
            
            with lock:
                final_preds.append({
                    "id": id,
                    "prediction": final_pred,
                })
                utils.dump_jsonl(final_preds, final_output_path)
            print(f"Final prediction for example {id}: {final_pred}")
            map_time += example_map_time
            reduce_time += example_reduce_time
        else:
            print(f"No result for example {id}")
    
    print(f"Processing {stop_idx - start_idx - len(processed_ids)} examples with {max_workers} workers...")
    print(f"Logs will be written to: {log_dir}")
    
    def process_example(i, examples, tokenizer, task, chunk_length, input_length, log_file=None):
        """Process a single example with the agent."""
        eg = examples[i]
        context = eg["context"]
        id = i
        question = eg.get("question", eg.get("input", ""))
        example_map_time = 0.0
        example_reduce_time = 0.0
        
        def log(msg):
            if log_file:
                with open(log_file, "a") as f:
                    f.write(f"[Example {id}] {msg}\n")
            print(f"[Example {id}] {msg}")
        
        log(f"Starting agent (question: {question[:100]}...)")
        
        try:
            # Create context manager
            manner = "front"  # RAG uses front truncation
            map_start = time.time()
            ctx = ContextManager(
                full_text=context,
                tokenizer=tokenizer,
                chunk_length=chunk_length,
                input_length=input_length,
                manner=manner
            )
            map_end = time.time()
            example_map_time += (map_end - map_start)
            
            log(f"Created context with {ctx.get_num_chunks()} chunks, {ctx.get_token_count()} tokens")
            
            # Create and run agent
            agent = MultihopAgent(
                client=utils.client,
                model=utils.model,
                tokenizer=tokenizer,
                max_steps=8,
                log_file=log_file
            )
            
            reduce_start = time.time()
            final_pred = agent.run(question, ctx)
            reduce_end = time.time()
            example_reduce_time += (reduce_end - reduce_start)
            
            log(f"Completed (map: {example_map_time:.2f}s, reduce: {example_reduce_time:.2f}s)")
            
            return id, final_pred, example_map_time, example_reduce_time
            
        except Exception as e:
            log(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(start_idx, stop_idx):
            if i in processed_ids:
                continue
            log_file = log_dir / f"example_{i}.log"
            future = executor.submit(
                process_example,
                i,
                examples,
                tokenizer,
                task,
                chunk_length,
                input_length,
                log_file=log_file,
            )
            futures.append(future)
        
        for future in as_completed(futures):
            try:
                result = future.result()
                process_result(result)
            except Exception as e:
                print(f"Exception occurred: {e}")
                import traceback
                traceback.print_exc()
    
    final_preds.sort(key=lambda x: x["id"])
    utils.dump_jsonl(final_preds, final_output_path)
    
    total_time = time.time() - start_time
    run_time_info = {
        "total_time": total_time,
        "map_time": map_time,
        "reduce_time": reduce_time
    }
    
    print(f"Total processing time: {total_time:.2f}s, Map time: {map_time:.2f}s, Reduce time: {reduce_time:.2f}s")
    print(f"Results saved to {output_dir}")
    
    return final_preds, run_time_info


@register("multihop")
def multihop_agent_runner(
    examples,
    tokenizer,
    task: str,
    chunk_length: int,
    input_length: int,
    output_dir,
    max_workers: int = 1,
    context_length: int = 128000,
    log_dir=None
):
    """Entry point for the multihop agent pipeline."""
    return run_agentic_pipeline(
        examples,
        tokenizer,
        task,
        chunk_length,
        input_length,
        output_dir,
        max_workers,
        context_length,
        log_dir
    )


@register("legacy")
def legacy_agent_runner(
    examples,
    tokenizer,
    task: str,
    chunk_length: int,
    input_length: int,
    output_dir,
    max_workers: int = 1,
    context_length: int = 128000,
    log_dir=None
):
    """Entry point for the legacy (map-reduce) pipeline."""
    from .. import pipeline
    return pipeline.run_pipeline(
        examples,
        tokenizer,
        task,
        chunk_length,
        input_length,
        output_dir,
        max_workers,
        context_length,
        log_dir
    )