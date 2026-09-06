"""C1 sliding-window overlap chunking (LangChain-backed).

Uses ``langchain_text_splitters.RecursiveCharacterTextSplitter`` with a
custom ``length_function`` backed by the pipeline's own tiktoken tokenizer,
so token accounting is identical to every other chunker.

The key parameter is ``overlap_ratio`` (default 0.5): the stride is
``chunk_length * (1 - overlap_ratio)``, so overlap_ratio=0.5 yields ~2x
the chunk count of the baseline.
"""

from __future__ import annotations

from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import register
from .. import utils as _utils


def _make_length_fn(tokenizer):
    """Return a length function that counts tokens via *tokenizer*."""
    def _length(text: str) -> int:
        return len(tokenizer.encode(text))
    return _length


# Default separators: paragraph break → sentence end → word boundary → char.
# Matches the English-only assumption of this study.
_DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@register("overlap")
def overlap_chunks(
    tokenizer,
    context: str,
    chunk_length: int,
    input_length: int,
    manner: str = "middle",
    overlap_ratio: float = 0.5,
) -> List[str]:
    """C1: fixed-size token chunks with sliding-window overlap.

    Parameters
    ----------
    overlap_ratio : float, optional
        Fraction of ``chunk_length`` that overlaps between consecutive chunks.
        ``overlap_ratio=0.5`` means each successive window advances by half
        the window, producing ~2x chunks.  Must be in [0, 1).
    """
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")
    if not (0.0 <= overlap_ratio < 1.0):
        raise ValueError("overlap_ratio must be in [0, 1)")

    if tokenizer is None:
        return _naive_overlap_chunks(context, chunk_length, overlap_ratio)

    # Truncate exactly like the baseline
    tokens = _utils.truncate_input(
        tokenizer.encode(context), input_length, manner=manner
    )
    text = tokenizer.decode(tokens)

    chunk_overlap_tokens = int(chunk_length * overlap_ratio)
    # LangChain expects chunk_overlap in the same units as chunk_size
    # (here: token count via our length function).
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_length,
        chunk_overlap=chunk_overlap_tokens,
        length_function=_make_length_fn(tokenizer),
        separators=_DEFAULT_SEPARATORS,
        is_separator_regex=False,
    )
    chunks = splitter.split_text(text)

    # Final clamp: LangChain's splitter may produce a trailing chunk slightly
    # over budget due to separator accounting.  Trim any offenders.
    clamped: List[str] = []
    for c in chunks:
        toks = tokenizer.encode(c)
        if len(toks) > chunk_length:
            c = tokenizer.decode(toks[:chunk_length])
        if c:
            clamped.append(c)
    return clamped


# ---- Naive fallback (no tokenizer) ----------------------------------------

def _naive_overlap_chunks(
    context: str, chunk_length: int, overlap_ratio: float
) -> List[str]:
    """Character-level sliding window when no tokenizer is supplied."""
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")
    stride = max(1, int(chunk_length * (1 - overlap_ratio)))
    chunks: List[str] = []
    i = 0
    while i < len(context):
        chunks.append(context[i : i + chunk_length])
        i += stride
    return chunks
