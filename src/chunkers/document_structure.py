"""C5 document-structure-aware chunking.

Detects explicit structural boundaries in English text via regex markers
(chapter headings, ALL-CAPS lines, Roman numerals, part headings, date
headings, and asterisk separator lines).  The text is split at detected
boundaries, oversized structural sections are recursively split, and tiny
sections are merged into neighbours.  When no markers are found the chunker
falls back to C3 (``recursive_paragraph``) so that structureless RAG data
never degrades below paragraph-aware splitting.
"""

from __future__ import annotations

import re
from typing import List, Optional, Pattern

from . import register
from .recursive_paragraph import _pack_units, recursive_paragraph_chunks
from .. import utils as _utils


# ---------------------------------------------------------------------------
# Default structural markers (line-matched)
# ---------------------------------------------------------------------------

_DEFAULT_MARKERS: List[Pattern[str]] = [
    # Asterisk separator line: * * * * *
    re.compile(r"^\*\s+\*\s+\*\s+\*\s+\*$"),
    # ALL-CAPS lines (titles/headings).  Allows common punctuation.
    re.compile(r"^[A-Z][A-Z0-9 ,.\-'\":;!?]{2,}$"),
    # Chapter N / CHAPTER N
    re.compile(r"^(?:Chapter|CHAPTER)\s+\d+"),
    # PART ONE / Part Two / PART I / Part II
    re.compile(
        r"^(?:PART|Part)\s+"
        r"(?:(?i:ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)|"
        r"[IVXLCDM]+)$"
    ),
    # Standalone Roman numerals (I, II, III, ..., C)
    re.compile(
        r"^(?=[IVXLCDM])"
        r"M{0,4}(?:CM|CD|D?C{0,3})"
        r"(?:XC|XL|L?X{0,3})"
        r"(?:IX|IV|V?I{0,3})$"
    ),
    # Date headings: MONDAY, JANUARY 1, 2024
    re.compile(r"^[A-Z]+,\s+[A-Z]+\s+\d{1,2},\s+\d{4}$"),
]


# ---------------------------------------------------------------------------
# Boundary detection
# ---------------------------------------------------------------------------

def _is_boundary_line(line: str, markers: List[Pattern[str]]) -> bool:
    """Return True if *line* matches any structural marker."""
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.fullmatch(stripped) for pattern in markers)


def _boundary_positions(
    text: str, markers: List[Pattern[str]]
) -> tuple[List[int], int]:
    """Return (sorted boundary offsets, number of marker lines found).

    The boundary list always contains 0 and ``len(text)``; the marker count
    tells the caller whether any structural boundary was actually detected
    (including boundaries at the very start or end of the text).
    """
    boundaries = {0, len(text)}
    marker_count = 0
    pos = 0
    for line in text.splitlines(keepends=True):
        if _is_boundary_line(line, markers):
            boundaries.add(pos)
            marker_count += 1
        pos += len(line)
    return sorted(boundaries), marker_count


def _split_at_boundaries(text: str, boundaries: List[int]) -> List[str]:
    """Slice *text* at boundary offsets, dropping empty pieces."""
    sections: List[str] = []
    for i in range(len(boundaries) - 1):
        piece = text[boundaries[i] : boundaries[i + 1]]
        if piece:
            sections.append(piece)
    return sections


# ---------------------------------------------------------------------------
# Registered chunker
# ---------------------------------------------------------------------------

@register("document_structure")
def document_structure_chunks(
    tokenizer,
    context: str,
    chunk_length: int,
    input_length: int,
    manner: str = "middle",
    markers: Optional[List[Pattern[str]]] = None,
) -> List[str]:
    """C5: document-structure-aware chunking.

    Parameters
    ----------
    markers : list[Pattern], optional
        Custom regex patterns to use as structural boundaries.  Each pattern
        is matched against a single stripped line via ``fullmatch``.  Defaults
        to a built-in set covering common English book/RAG headings.
    """
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")

    if tokenizer is None:
        return _naive_document_structure_chunks(context, chunk_length, markers)

    # Phase 0: truncate exactly like the baseline and C3.
    tokens = _utils.truncate_input(
        tokenizer.encode(context), input_length, manner=manner
    )
    text = tokenizer.decode(tokens)

    if not text.strip():
        return []

    markers = markers if markers is not None else _DEFAULT_MARKERS
    boundaries, marker_count = _boundary_positions(text, markers)

    # Phase 1: no structural markers -> fall back to paragraph-aware C3.
    if marker_count == 0:
        return recursive_paragraph_chunks(
            tokenizer, context, chunk_length, input_length, manner
        )

    # Phase 2: pack structural sections, recursively split oversized ones.
    sections = _split_at_boundaries(text, boundaries)
    return _pack_units(sections, tokenizer, chunk_length)


# ---------------------------------------------------------------------------
# Naive fallback (no tokenizer)
# ---------------------------------------------------------------------------

def _naive_document_structure_chunks(
    context: str,
    chunk_length: int,
    markers: Optional[List[Pattern[str]]] = None,
) -> List[str]:
    """Character-level structural splitting when no tokenizer is supplied."""
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")

    if not context.strip():
        return []

    markers = markers if markers is not None else _DEFAULT_MARKERS
    boundaries, marker_count = _boundary_positions(context, markers)

    if marker_count == 0:
        return _naive_paragraph_pack(context, chunk_length)

    sections = _split_at_boundaries(context, boundaries)
    chunks: List[str] = []
    current = ""
    for sec in sections:
        if len(sec) > chunk_length:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(sec[i : i + chunk_length] for i in range(0, len(sec), chunk_length))
            continue
        if current and len(current) + len(sec) > chunk_length:
            chunks.append(current)
            current = sec
        else:
            current = current + sec if current else sec
    if current:
        chunks.append(current)
    return chunks


def _naive_paragraph_pack(context: str, chunk_length: int) -> List[str]:
    """Character-level paragraph-aware fallback (mirrors C3 no-tokenizer)."""
    paragraphs = re.split(r"(\n\s*\n)", context)
    # Attach separators to preceding paragraph.
    pieces: List[str] = []
    i = 0
    while i < len(paragraphs):
        piece = paragraphs[i]
        if i + 1 < len(paragraphs):
            piece += paragraphs[i + 1]
            i += 2
        else:
            i += 1
        if piece:
            pieces.append(piece)

    chunks: List[str] = []
    current = ""
    for piece in pieces:
        if len(piece) > chunk_length:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(piece[i : i + chunk_length] for i in range(0, len(piece), chunk_length))
            continue
        if current and len(current) + len(piece) > chunk_length:
            chunks.append(current)
            current = piece
        else:
            current = current + piece if current else piece
    if current:
        chunks.append(current)
    return chunks
