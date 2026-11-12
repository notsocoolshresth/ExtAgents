"""Context manager for the agentic pipeline.

Handles full text storage, chunking, BM25 indexing, and range reading.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

import tiktoken
from rank_bm25 import BM25Okapi


@dataclass
class SearchResult:
    """Result from BM25 search."""
    chunk_id: int
    score: float
    preview: str


@dataclass
class ChunkResult:
    """Result from reading a chunk."""
    chunk_id: int
    text: str
    token_start: int
    token_end: int


@dataclass
class RangeResult:
    """Result from reading a token range."""
    text: str
    token_start: int
    token_end: int


class ContextManager:
    """Manages the full context text, chunking, and search index."""
    
    def __init__(
        self,
        full_text: str,
        tokenizer,
        chunk_length: int,
        input_length: int,
        manner: str = "front"
    ):
        self.full_text = full_text
        self.tokenizer = tokenizer
        self.chunk_length = chunk_length
        self.input_length = input_length
        self.manner = manner
        
        # Tokenize and truncate
        self.tokens = self._tokenize_and_truncate(full_text)
        
        # Create chunks
        self.chunks = self._create_chunks()
        self.chunk_texts = [tokenizer.decode(c) for c in self.chunks]
        
        # Build BM25 index
        self.bm25 = self._build_bm25_index()
    
    def _tokenize_and_truncate(self, text: str) -> List[int]:
        """Tokenize text and truncate to input_length."""
        tokens = self.tokenizer.encode(text)
        if len(tokens) > self.input_length:
            if self.manner == "front":
                tokens = tokens[:self.input_length]
            elif self.manner == "middle":
                half = self.input_length // 2
                tokens = tokens[:half] + tokens[-half:]
            else:
                tokens = tokens[:self.input_length]
        return tokens
    
    def _create_chunks(self) -> List[List[int]]:
        """Split tokens into chunks of chunk_length."""
        return [
            self.tokens[i:i + self.chunk_length]
            for i in range(0, len(self.tokens), self.chunk_length)
        ]
    
    def _build_bm25_index(self) -> BM25Okapi:
        """Build BM25 index over chunk texts."""
        tokenized_chunks = [self._tokenize_for_bm25(text) for text in self.chunk_texts]
        return BM25Okapi(tokenized_chunks)
    
    def _tokenize_for_bm25(self, text: str) -> List[str]:
        """Simple tokenization for BM25 (word-level)."""
        # Split on whitespace and punctuation, keep alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def get_num_chunks(self) -> int:
        """Return the number of chunks."""
        return len(self.chunks)
    
    def get_chunk(self, chunk_id: int) -> ChunkResult:
        """Get a full chunk by ID."""
        if chunk_id < 0 or chunk_id >= len(self.chunks):
            raise IndexError(f"Chunk ID {chunk_id} out of range [0, {len(self.chunks)})")
        
        # Calculate token start/end
        token_start = chunk_id * self.chunk_length
        token_end = min(token_start + self.chunk_length, len(self.tokens))
        
        return ChunkResult(
            chunk_id=chunk_id,
            text=self.chunk_texts[chunk_id],
            token_start=token_start,
            token_end=token_end
        )
    
    def get_range(self, start_token: int, end_token: int) -> RangeResult:
        """Get an arbitrary token range."""
        start_token = max(0, min(start_token, len(self.tokens)))
        end_token = max(start_token, min(end_token, len(self.tokens)))
        
        text = self.tokenizer.decode(self.tokens[start_token:end_token])
        return RangeResult(
            text=text,
            token_start=start_token,
            token_end=end_token
        )
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Search for relevant chunks using BM25."""
        if top_k <= 0:
            return []
        
        tokenized_query = self._tokenize_for_bm25(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            preview = self.chunk_texts[idx][:200]
            results.append(SearchResult(
                chunk_id=idx,
                score=float(scores[idx]),
                preview=preview
            ))
        
        return results
    
    def get_full_text(self) -> str:
        """Get the full (truncated) text."""
        return self.tokenizer.decode(self.tokens)
    
    def get_token_count(self) -> int:
        """Get total token count after truncation."""
        return len(self.tokens)