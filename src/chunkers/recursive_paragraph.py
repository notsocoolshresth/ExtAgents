"""C3 recursive paragraph-aware chunking."""

import re

from . import register
from .. import utils as _utils


_FINE_SPLITS = (
    re.compile(r"(?<=[.!?])(\s+)"),
    re.compile(r"(\s+)"),
)
_PARAGRAPH_SPLIT = re.compile(r"(\n\s*\n)")


@register("recursive_paragraph")
def recursive_paragraph_chunks(tokenizer, context, chunk_length, input_length, manner="middle"):
    """C3: paragraph-aware recursive packing (English-only).

    Truncates to `input_length` exactly as the baseline does, then greedily
    packs whole paragraphs up to `chunk_length` tokens. A single unit larger
    than `chunk_length` recurses into sentences, then into whitespace-delimited
    words, then into fixed-size token slices. Every assembled chunk is
    re-encoded and clamped to the token budget so the MAP stage never sees an
    oversized chunk.
    """
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")
    if tokenizer is None:
        return _naive_paragraph_chunks(context, chunk_length)
    tokens = _utils.truncate_input(tokenizer.encode(context), input_length, manner=manner)
    paragraphs = _split_keep_separators(tokenizer.decode(tokens), _PARAGRAPH_SPLIT)
    return _pack_units(paragraphs, tokenizer, chunk_length)


def _split_keep_separators(text, pattern):
    """Split `text` on `pattern` (single capture group = separator), attaching each
    separator to the text preceding it. Empty pieces are dropped."""
    parts = re.split(pattern, text)
    merged = []
    i = 0
    while i < len(parts):
        piece = parts[i]
        if i + 1 < len(parts):
            piece += parts[i + 1]
            i += 2
        else:
            i += 1
        if piece:
            merged.append(piece)
    return merged


def _join_within_budget(pieces, tokenizer, chunk_length):
    text = "".join(pieces)
    if len(tokenizer.encode(text)) > chunk_length:
        tokens = tokenizer.encode(text)
        text = tokenizer.decode(tokens[:chunk_length])
    return text


def _pack_units(pieces, tokenizer, chunk_length):
    """Greedily pack text pieces into chunks of at most `chunk_length` tokens.
    Pieces larger than the budget are handed to `_split_finer` recursively."""
    chunks, current, current_tokens = [], [], 0
    for piece in pieces:
        n = len(tokenizer.encode(piece))
        if n > chunk_length:
            if current:
                chunks.append(_join_within_budget(current, tokenizer, chunk_length))
                current, current_tokens = [], 0
            chunks.extend(_split_finer(piece, tokenizer, chunk_length))
            continue
        if current and current_tokens + n > chunk_length:
            chunks.append(_join_within_budget(current, tokenizer, chunk_length))
            current, current_tokens = [], 0
        current.append(piece)
        current_tokens += n
    if current:
        chunks.append(_join_within_budget(current, tokenizer, chunk_length))
    return chunks


def _split_finer(piece, tokenizer, chunk_length):
    """Recursively split an oversized unit: sentences, then words, then token slices."""
    for pattern in _FINE_SPLITS:
        sub_pieces = _split_keep_separators(piece, pattern)
        if len(sub_pieces) > 1:
            return _pack_units(sub_pieces, tokenizer, chunk_length)
    return _fixed_slices(piece, tokenizer, chunk_length)


def _fixed_slices(text, tokenizer, chunk_length):
    tokens = tokenizer.encode(text)
    return [
        tokenizer.decode(tokens[i : i + chunk_length])
        for i in range(0, len(tokens), chunk_length)
    ]


def _naive_paragraph_chunks(context, chunk_length):
    """Fallback when no tokenizer is supplied (character-level packing)."""
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")
    paragraphs = _split_keep_separators(context, _PARAGRAPH_SPLIT)
    chunks, current, current_len = [], [], 0
    for piece in paragraphs:
        if len(piece) > chunk_length:
            if current:
                chunks.append("".join(current))
                current, current_len = [], 0
            chunks.extend(
                piece[i : i + chunk_length] for i in range(0, len(piece), chunk_length)
            )
            continue
        if current and current_len + len(piece) > chunk_length:
            chunks.append("".join(current))
            current, current_len = [], 0
        current.append(piece)
        current_len += len(piece)
    if current:
        chunks.append("".join(current))
    return chunks
