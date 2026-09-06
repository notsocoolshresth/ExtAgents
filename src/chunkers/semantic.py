"""C4 semantic breakpoint chunking (LangChain-backed).

Uses ``langchain_experimental.text_splitter.SemanticChunker`` to embed
sliding windows of sentences and cut at cosine-similarity minima, then
enforces the token budget via a secondary ``RecursiveCharacterTextSplitter``
pass (same one used by C1).

Embedding model is configurable for ablation (default:
``sentence-transformers/all-MiniLM-L6-v2``).  The model is loaded lazily
on first call and cached for the process lifetime.
"""

from __future__ import annotations

import re
import warnings
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import register
from .. import utils as _utils

try:
    from langchain_experimental.text_splitter import SemanticChunker
except ImportError:
    SemanticChunker = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Lazy embedder cache (avoids re-loading the model on every call)
# ---------------------------------------------------------------------------

_embedder_cache: dict = {}


def _get_embedder(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
):
    """Return a cached ``HuggingFaceEmbeddings`` instance for *model_name*."""
    if model_name not in _embedder_cache:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embedder_cache[model_name] = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedder_cache[model_name]


# ---------------------------------------------------------------------------
# Token-length function (reused from C1 overlap chunker pattern)
# ---------------------------------------------------------------------------

def _make_length_fn(tokenizer):
    def _length(text: str) -> int:
        return len(tokenizer.encode(text))
    return _length


_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+")


# ---------------------------------------------------------------------------
# Registered chunker
# ---------------------------------------------------------------------------

@register("semantic")
def semantic_chunks(
    tokenizer,
    context: str,
    chunk_length: int,
    input_length: int,
    manner: str = "middle",
    embedder_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    breakpoint_threshold_type: str = "percentile",
    breakpoint_threshold_amount: Optional[float] = 85,
    buffer_size: int = 1,
) -> List[str]:
    """C4: semantic breakpoint chunking.

    1. Truncate to *input_length* (baseline-compatible).
    2. Split by semantic distance (``SemanticChunker``).
    3. Enforce token budget: split oversized chunks, merge tiny ones.

    Parameters
    ----------
    embedder_model : str
        HuggingFace model name for embeddings (ablation knob).
    breakpoint_threshold_type : str
        ``"percentile"`` | ``"standard_deviation"`` | ``"interquartile"`` | ``"gradient"``.
    breakpoint_threshold_amount : float or None
        Threshold for the chosen breakpoint type.  ``None`` = library default.
    buffer_size : int
        Context-window size around each sentence for embedding (1 = 3-sent window).
    """
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")

    if tokenizer is None:
        return _naive_semantic_chunks(context, chunk_length)

    # --- Phase 0: truncate exactly like the baseline ----------------------
    tokens = _utils.truncate_input(
        tokenizer.encode(context), input_length, manner=manner
    )
    text = tokenizer.decode(tokens)

    if not text.strip():
        return []

    # --- Phase 1: semantic splitting --------------------------------------
    if SemanticChunker is None:
        raise ImportError(
            "langchain-experimental is required for the semantic chunker. "
            "Install it with: pip install langchain-experimental"
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        embedder = _get_embedder(embedder_model)
        semantic_splitter = SemanticChunker(
            embedder,
            buffer_size=buffer_size,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
            sentence_split_regex=_SENTENCE_RE.pattern,
        )
        raw_chunks = semantic_splitter.split_text(text)

    if not raw_chunks:
        return []

    # --- Phase 2: enforce token budget ------------------------------------
    return _enforce_budget(raw_chunks, tokenizer, chunk_length)


def _enforce_budget(chunks: List[str], tokenizer, chunk_length: int) -> List[str]:
    """Split any chunk exceeding *chunk_length* tokens; merge tiny trailing chunks."""
    length_fn = _make_length_fn(tokenizer)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_length,
        chunk_overlap=0,
        length_function=length_fn,
        separators=_DEFAULT_SEPARATORS,
        is_separator_regex=False,
    )

    result: List[str] = []
    for chunk in chunks:
        n = len(tokenizer.encode(chunk))
        if n > chunk_length:
            # Oversized: split recursively (no overlap — semantic boundaries already found)
            sub = splitter.split_text(chunk)
            for s in sub:
                toks = tokenizer.encode(s)
                if len(toks) > chunk_length:
                    s = tokenizer.decode(toks[:chunk_length])
                if s:
                    result.append(s)
        elif chunk.strip():
            result.append(chunk)

    # Merge trailing tiny chunks (< 10% of budget) into the previous chunk
    if result:
        min_tokens = max(1, chunk_length // 10)
        merged: List[str] = [result[0]]
        for c in result[1:]:
            c_tokens = len(tokenizer.encode(c))
            if c_tokens < min_tokens and merged:
                prev = merged[-1]
                combined = prev + "\n" + c
                if len(tokenizer.encode(combined)) <= chunk_length:
                    merged[-1] = combined
                else:
                    merged.append(c)
            else:
                merged.append(c)
        result = merged

    return result


# ---------------------------------------------------------------------------
# Naive fallback (no tokenizer, no embedding model)
# ---------------------------------------------------------------------------

def _naive_semantic_chunks(context: str, chunk_length: int) -> List[str]:
    """Sentence-based fallback when no tokenizer is supplied."""
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")
    sentences = re.split(r"(?<=[.?!])\s+", context)
    chunks: List[str] = []
    current = ""
    for s in sentences:
        if len(current) + len(s) > chunk_length and current:
            chunks.append(current)
            current = s
        else:
            current = (current + " " + s).strip() if current else s
    if current:
        chunks.append(current)
    return chunks
