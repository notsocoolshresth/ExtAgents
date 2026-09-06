"""Pluggable chunking strategies for the ExtAgents map-reduce pipeline (P2).

Each chunker implements the `utils.create_chunks` interface:

    create_chunks(tokenizer, context, chunk_length, input_length, manner="middle") -> list[str]

so the runner (`src/pipeline.py`) is untouched: `install(id)` hot-swaps
`src.utils.create_chunks` (which the pipeline resolves dynamically per example),
and `main.py --chunker <id>` performs the selection at the CLI entry.
"""

from typing import Callable, Dict, List

from .. import utils as _utils


_BASELINE_CREATE_CHUNKS = _utils.create_chunks

_CHUNKERS: Dict[str, Callable] = {}


def register(chunker_id: str) -> Callable:
    """Decorator registering a chunker implementation under `chunker_id`."""

    def decorator(func: Callable) -> Callable:
        if chunker_id in _CHUNKERS:
            raise ValueError(f"chunker {chunker_id!r} already registered")
        _CHUNKERS[chunker_id] = func
        return func

    return decorator


def available() -> List[str]:
    """Aliases of registered chunkers, sorted."""
    return sorted(_CHUNKERS)


def get(chunker_id: str) -> Callable:
    """Return the registered chunker callable."""
    if chunker_id not in _CHUNKERS:
        raise ValueError(f"unknown chunker {chunker_id!r}; available: {available()}")
    return _CHUNKERS[chunker_id]


def install(chunker_id: str) -> Callable:
    """Activate `chunker_id` as the pipeline's chunker.

    Replaces `src.utils.create_chunks`, which `src/pipeline.py` resolves
    dynamically for every example (`src/pipeline.py:47`), so runner code stays
    untouched. `restore()` (or re-`install()`) switches back. Returns the now
    active callable.
    """
    func = get(chunker_id)
    _utils.create_chunks = func
    return func


def restore() -> None:
    """Restore the original baseline `utils.create_chunks`."""
    _utils.create_chunks = _BASELINE_CREATE_CHUNKS


from . import legacy, overlap, recursive_paragraph  # noqa: E402,F401
