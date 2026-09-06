"""C0 legacy fixed-size token chunking."""

from . import register
from .. import utils


@register("legacy")
def legacy_create_chunks(tokenizer, context, chunk_length, input_length, manner="middle"):
    """C0 baseline: fixed-size token blocks, byte-identical to `utils.create_chunks`."""
    if tokenizer is None:
        return utils.chunk_input(context, chunk_length)

    tokens = tokenizer.encode(context)
    tokens = utils.truncate_input(tokens, input_length, manner=manner)
    token_chunks = utils.chunk_input(tokens, chunk_length)
    return [tokenizer.decode(chunk) for chunk in token_chunks]
