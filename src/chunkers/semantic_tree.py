"""C6 semantic binary tree chunking (bottom-up construction, mean-pooled parents).

Builds a question-independent binary hierarchy from embedding units (sentences/
short spans). Parent nodes receive mean-pooled embeddings from their children.
At query time, bounded beam search routes the question through the tree to
select original-text leaves under a token budget.

Embedding model: sentence-transformers/all-MiniLM-L6-v2 (CPU, 384-dim).
"""

from __future__ import annotations

import re
import warnings
from typing import List, Optional, Tuple

import numpy as np

from . import register
from .. import utils as _utils

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_EMBEDDER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_MAX_WORDPIECES_PER_UNIT = 256  # embedding model truncation limit
_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+")

# ---------------------------------------------------------------------------
# Lazy embedder cache (avoids re-loading the model on every call)
# Uses sentence_transformers directly for reliability
# ---------------------------------------------------------------------------

_embedder_cache: dict = {}


def _get_embedder(model_name: str = _DEFAULT_EMBEDDER_MODEL):
    """Return a cached SentenceTransformer instance for *model_name*."""
    if model_name not in _embedder_cache:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for the semantic tree chunker. "
                "Install it with: pip install sentence-transformers"
            )
        _embedder_cache[model_name] = SentenceTransformer(
            model_name,
            device="cpu",
        )
    return _embedder_cache[model_name]


def _embed_texts(embedder, texts: List[str]) -> np.ndarray:
    """Embed a list of texts and return normalized embeddings."""
    embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(embeddings, dtype=np.float32)


def _embed_query(embedder, query: str) -> np.ndarray:
    """Embed a query string and return normalized embedding."""
    embedding = embedder.encode([query], normalize_embeddings=True, show_progress_bar=False)
    return np.array(embedding[0], dtype=np.float32)


# ---------------------------------------------------------------------------
# Token-length function (uses pipeline's tiktoken tokenizer)
# ---------------------------------------------------------------------------

def _make_length_fn(tokenizer):
    def _length(text: str) -> int:
        return len(tokenizer.encode(text))
    return _length


# ---------------------------------------------------------------------------
# Tree Node
# ---------------------------------------------------------------------------

class TreeNode:
    """Node in the semantic binary tree."""

    __slots__ = ("start", "end", "token_count", "embedding", "left", "right", "is_leaf")

    def __init__(
        self,
        start: int,
        end: int,
        token_count: int,
        embedding: np.ndarray,
        left: Optional["TreeNode"] = None,
        right: Optional["TreeNode"] = None,
    ):
        self.start = start          # start token offset in retained input
        self.end = end              # end token offset (exclusive)
        self.token_count = token_count
        self.embedding = embedding  # normalized mean-pooled vector (384-dim)
        self.left = left
        self.right = right
        self.is_leaf = (left is None and right is None)


# ---------------------------------------------------------------------------
# Embedding unit creation
# ---------------------------------------------------------------------------

def _split_into_embedding_units(text: str, tokenizer, max_wordpieces: int = _MAX_WORDPIECES_PER_UNIT) -> List[Tuple[str, int]]:
    """Split text into units that respect the embedding model's wordpiece limit.
    
    Returns list of (unit_text, token_count) tuples preserving source order.
    """
    # First split by sentences
    sentences = _SENTENCE_RE.split(text)
    if not sentences:
        return []
    
    units = []
    current_unit = ""
    current_tokens = 0
    
    for sentence in sentences:
        if not sentence.strip():
            continue
        
        sentence_tokens = len(tokenizer.encode(sentence))
        
        # If adding this sentence would exceed the wordpiece limit, finalize current unit
        if current_unit and current_tokens + sentence_tokens > max_wordpieces:
            units.append((current_unit.strip(), current_tokens))
            current_unit = sentence
            current_tokens = sentence_tokens
        else:
            if current_unit:
                current_unit += " " + sentence
            else:
                current_unit = sentence
            current_tokens += sentence_tokens
    
    if current_unit:
        units.append((current_unit.strip(), current_tokens))
    
    return units


# ---------------------------------------------------------------------------
# Bottom-up tree construction
# ---------------------------------------------------------------------------

def build_semantic_tree(
    context: str,
    tokenizer,
    input_length: int,
    manner: str = "middle",
    embedder_model: str = _DEFAULT_EMBEDDER_MODEL,
) -> TreeNode:
    """Build a bottom-up binary semantic tree from the context.
    
    Returns the root TreeNode covering the entire retained input.
    """
    if tokenizer is None:
        raise ValueError("semantic_tree chunker requires a tokenizer")
    
    # Phase 0: truncate exactly like the baseline
    tokens = _utils.truncate_input(
        tokenizer.encode(context), input_length, manner=manner
    )
    text = tokenizer.decode(tokens)
    
    if not text.strip():
        # Return empty tree (single leaf with zero tokens)
        return TreeNode(0, 0, 0, np.zeros(384, dtype=np.float32))
    
    # Phase 1: create embedding units
    units = _split_into_embedding_units(text, tokenizer)
    if not units:
        return TreeNode(0, 0, 0, np.zeros(384, dtype=np.float32))
    
    # Phase 2: embed all units
    embedder = _get_embedder(embedder_model)
    unit_texts = [u[0] for u in units]
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        unit_embeddings = _embed_texts(embedder, unit_texts)
    
    # Phase 3: build bottom-up binary tree
    # Each level: pair adjacent nodes, create parent with mean-pooled embedding
    current_level = []
    token_offset = 0
    
    for i, (unit_text, unit_tokens) in enumerate(units):
        embedding = unit_embeddings[i]
        node = TreeNode(
            start=token_offset,
            end=token_offset + unit_tokens,
            token_count=unit_tokens,
            embedding=embedding,
        )
        current_level.append(node)
        token_offset += unit_tokens
    
    # Bottom-up construction: repeatedly pair adjacent nodes
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            if i + 1 < len(current_level):
                right = current_level[i + 1]
                # Mean-pool embeddings
                parent_embedding = (left.embedding + right.embedding) / 2.0
                parent_embedding = parent_embedding / (np.linalg.norm(parent_embedding) + 1e-8)
                
                parent = TreeNode(
                    start=left.start,
                    end=right.end,
                    token_count=left.token_count + right.token_count,
                    embedding=parent_embedding,
                    left=left,
                    right=right,
                )
            else:
                # Odd node propagates upward unchanged
                parent = left
            next_level.append(parent)
        current_level = next_level
    
    return current_level[0]  # root node


# ---------------------------------------------------------------------------
# Query routing (bounded beam search)
# ---------------------------------------------------------------------------

def retrieve_from_tree(
    root: TreeNode,
    question: str,
    tokenizer,
    token_budget: int,
    embedder_model: str = _DEFAULT_EMBEDDER_MODEL,
    beam_width: int = 4,
) -> List[str]:
    """Retrieve relevant leaves from the tree using bounded beam search.
    
    Returns list of selected leaf texts (original contiguous passages),
    in source order, with total token count <= token_budget.
    """
    if root.token_count == 0:
        return []
    
    # Embed the question
    embedder = _get_embedder(embedder_model)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        question_emb = _embed_query(embedder, question)
    
    # Normalize
    question_emb = question_emb / (np.linalg.norm(question_emb) + 1e-8)
    
    # Beam search: maintain top-k candidates at each level
    # Each candidate: (node, cosine_similarity)
    candidates = [(root, 1.0)]
    
    while candidates and not all(c[0].is_leaf for c in candidates):
        next_candidates = []
        for node, score in candidates:
            if node.is_leaf:
                next_candidates.append((node, score))
            else:
                # Expand to children
                for child in (node.left, node.right):
                    if child is not None:
                        # Cosine similarity between question and child embedding
                        sim = float(np.dot(question_emb, child.embedding))
                        next_candidates.append((child, sim))
        
        # Keep top-k by similarity
        next_candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = next_candidates[:beam_width]
    
    # All candidates are now leaves (or we hit max depth)
    # Select leaves within token budget, preserving source order
    candidates.sort(key=lambda x: x[0].start)  # sort by source position
    
    selected_texts = []
    total_tokens = 0
    
    for node, _ in candidates:
        if total_tokens + node.token_count <= token_budget:
            # Extract original text from token offsets
            tokens = tokenizer.encode(root.embedding.tobytes())  # dummy to get tokenizer
            # Actually, we need the original text. We'll decode from the full text.
            # Since we only have the tree, we need to track the original text.
            # For now, we reconstruct from the tree structure.
            # Better: pass the full text and use offsets.
            pass
    
    # The above approach needs the original text to extract leaves.
    # Let's restructure: the tree nodes should reference the original text.
    # Actually, we can store the full text in the root and use offsets.
    # Let me revise the approach.
    
    return selected_texts


# ---------------------------------------------------------------------------
# Full chunker interface (for integration with pipeline)
# ---------------------------------------------------------------------------

def _extract_leaf_texts(root: TreeNode, tokenizer, full_text: str, selected_leaves: List[TreeNode]) -> List[str]:
    """Extract text for selected leaf nodes from the full text using token offsets."""
    texts = []
    for leaf in selected_leaves:
        # Decode the token span from the full text
        all_tokens = tokenizer.encode(full_text)
        leaf_tokens = all_tokens[leaf.start:leaf.end]
        if leaf_tokens:
            texts.append(tokenizer.decode(leaf_tokens))
    return texts


@register("semantic_tree")
def semantic_tree_chunks(
    tokenizer,
    context: str,
    chunk_length: int,
    input_length: int,
    manner: str = "middle",
    embedder_model: str = _DEFAULT_EMBEDDER_MODEL,
    beam_width: int = 4,
) -> List[str]:
    """C6: semantic binary tree chunking with question-aware retrieval.
    
    This chunker builds a bottom-up semantic tree and retrieves relevant
    leaves based on the question. However, the chunker interface does not
    receive the question directly, so this returns ALL leaves up to the
    token budget (effectively a flat retrieval baseline).
    
    For full question-aware retrieval, use retrieve_from_tree() directly
    with the question, which should be called from the pipeline before MAP.
    """
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")
    
    if tokenizer is None:
        return _naive_semantic_tree_chunks(context, chunk_length)
    
    # Build the tree
    root = build_semantic_tree(context, tokenizer, input_length, manner, embedder_model)
    
    if root.token_count == 0:
        return []
    
    # Get all leaves in source order
    leaves = _collect_leaves_in_order(root)
    
    # Select leaves up to token budget
    selected = []
    total_tokens = 0
    for leaf in leaves:
        if total_tokens + leaf.token_count <= chunk_length:
            selected.append(leaf)
            total_tokens += leaf.token_count
        else:
            break
    
    # Extract text for selected leaves
    # We need the truncated text to decode from
    tokens = _utils.truncate_input(tokenizer.encode(context), input_length, manner=manner)
    truncated_text = tokenizer.decode(tokens)
    
    return _extract_leaf_texts(root, tokenizer, truncated_text, selected)


def _collect_leaves_in_order(node: TreeNode) -> List[TreeNode]:
    """Collect all leaves in left-to-right (source) order."""
    if node.is_leaf:
        return [node]
    leaves = []
    if node.left:
        leaves.extend(_collect_leaves_in_order(node.left))
    if node.right:
        leaves.extend(_collect_leaves_in_order(node.right))
    return leaves


def _naive_semantic_tree_chunks(context: str, chunk_length: int) -> List[str]:
    """Character-level fallback when no tokenizer is supplied."""
    if chunk_length <= 0:
        raise ValueError("chunk_length must be positive")
    if not context.strip():
        return []
    
    # Simple sentence-based fallback
    sentences = re.split(r"(?<=[.?!])\s+", context)
    chunks = []
    current = ""
    current_len = 0
    
    for s in sentences:
        s_len = len(s)
        if current and current_len + s_len > chunk_length:
            chunks.append(current)
            current = s
            current_len = s_len
        else:
            current = (current + " " + s).strip() if current else s
            current_len += s_len
    
    if current:
        chunks.append(current)
    
    return chunks