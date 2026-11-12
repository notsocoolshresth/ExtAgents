"""Pluggable agentic strategies for the ExtAgents pipeline.

Each agent implements the `pipeline.run_pipeline` interface:

    run_pipeline(examples, tokenizer, task, chunk_length, input_length,
                 output_dir, max_workers=1, context_length=128000, log_dir=None)
                 -> (list[dict], dict)

so the CLI (`main.py`) stays untouched: `install(agent_id)` hot-swaps
`src.pipeline.run_pipeline`, and `main.py --agent <id>` performs the selection.
"""

from typing import Callable, Dict, List

from .. import pipeline as _pipeline


_BASELINE_RUN_PIPELINE = _pipeline.run_pipeline

_AGENTS: Dict[str, Callable] = {}


def register(agent_id: str) -> Callable:
    """Decorator registering an agent implementation under `agent_id`."""

    def decorator(func: Callable) -> Callable:
        if agent_id in _AGENTS:
            raise ValueError(f"agent {agent_id!r} already registered")
        _AGENTS[agent_id] = func
        return func

    return decorator


def available() -> List[str]:
    """Aliases of registered agents, sorted."""
    return sorted(_AGENTS)


def get(agent_id: str) -> Callable:
    """Return the registered agent callable."""
    if agent_id not in _AGENTS:
        raise ValueError(f"unknown agent {agent_id!r}; available: {available()}")
    return _AGENTS[agent_id]


def install(agent_id: str) -> Callable:
    """Activate `agent_id` as the pipeline's runner.

    Replaces `src.pipeline.run_pipeline`, which `main.py` calls directly.
    `restore()` (or re-`install()`) switches back. Returns the now active callable.
    """
    func = get(agent_id)
    _pipeline.run_pipeline = func
    return func


def restore() -> None:
    """Restore the original baseline `pipeline.run_pipeline`."""
    _pipeline.run_pipeline = _BASELINE_RUN_PIPELINE


from . import multihop_agent  # noqa: E402,F401