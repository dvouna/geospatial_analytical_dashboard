"""
Semantic Query Cache for LLM Code Generation.
Uses text embeddings to perform cosine similarity searches, saving API requests
and eliminating latency for similar queries.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from utils.paths import data_path


class SemanticCodeCache:
    """Embedding-based cache to store and retrieve generated Pandas code snippets."""

    def __init__(self, cache_filename: str = "semantic_cache.json", threshold: float = 0.93):
        self.cache_path = data_path() / cache_filename
        self.threshold = threshold
        self.cache: list[dict[str, Any]] = []
        self.load_cache()

    def load_cache(self) -> None:
        """Load cached queries from JSON file."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = []
        else:
            self.cache = []

    def save_cache(self) -> None:
        """Persist cached queries to JSON file."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Compute the cosine similarity between two vector lists."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def get_cached_code(self, query_vector: list[float]) -> Optional[Tuple[str, float]]:
        """
        Check if a query vector matches any cached query above the similarity threshold.

        Returns:
            Tuple of (pandas_code, similarity_score) if found, otherwise None.
        """
        if not self.cache or not query_vector:
            return None

        best_match_code = None
        best_similarity = -1.0

        for entry in self.cache:
            cached_vector = entry.get("embedding")
            if cached_vector:
                sim = self._cosine_similarity(query_vector, cached_vector)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match_code = entry.get("pandas_code")

        if best_similarity >= self.threshold and best_match_code:
            return best_match_code, best_similarity

        return None

    def add_to_cache(self, query: str, query_vector: list[float], code: str) -> None:
        """Save a new query text, vector embedding, and verified code to the cache."""
        if not query or not query_vector or not code:
            return

        # Avoid duplicates for identical queries
        self.cache = [e for e in self.cache if e.get("query").lower() != query.lower()]

        self.cache.append({
            "query": query,
            "embedding": query_vector,
            "pandas_code": code
        })
        self.save_cache()

    def clear_cache(self) -> None:
        """Clear all cache records and delete the cache file."""
        self.cache = []
        if self.cache_path.exists():
            try:
                self.cache_path.unlink()
            except Exception:
                pass
        self.save_cache()
