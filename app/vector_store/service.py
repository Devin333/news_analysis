"""Vector Store Service for storing and querying embeddings.

Provides an abstraction layer for vector storage, currently
supporting in-memory storage with plans for pgvector integration.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""

    id: str
    score: float
    metadata: dict[str, Any]


class VectorStoreService:
    """Service for vector storage and similarity search.

    Currently implements in-memory storage. Can be extended
    to support pgvector or other vector databases.
    """

    def __init__(self) -> None:
        """Initialize the vector store."""
        # In-memory storage: {namespace: {id: (vector, metadata)}}
        self._store: dict[str, dict[str, tuple[list[float], dict[str, Any]]]] = {}

    async def upsert(
        self,
        namespace: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert or update a vector.

        Args:
            namespace: Namespace for the vector (e.g., "topics", "items").
            id: Unique identifier for the vector.
            vector: The embedding vector.
            metadata: Optional metadata to store with the vector.
        """
        if namespace not in self._store:
            self._store[namespace] = {}

        self._store[namespace][id] = (vector, metadata or {})
        logger.debug(f"Upserted vector {id} in namespace {namespace}")

    async def delete(
        self,
        namespace: str,
        id: str,
    ) -> bool:
        """Delete a vector.

        Args:
            namespace: Namespace for the vector.
            id: Unique identifier for the vector.

        Returns:
            True if deleted, False if not found.
        """
        if namespace not in self._store:
            return False

        if id not in self._store[namespace]:
            return False

        del self._store[namespace][id]
        return True

    async def search(
        self,
        namespace: str,
        query_vector: list[float],
        limit: int = 10,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar vectors.

        Args:
            namespace: Namespace to search in.
            query_vector: Query embedding vector.
            limit: Maximum number of results.
            filter_metadata: Optional metadata filter.

        Returns:
            List of VectorSearchResult sorted by similarity.
        """
        if namespace not in self._store:
            return []

        results: list[tuple[str, float, dict[str, Any]]] = []
        query_np = np.array(query_vector)

        for id, (vector, metadata) in self._store[namespace].items():
            # Apply metadata filter if provided
            if filter_metadata:
                if not self._matches_filter(metadata, filter_metadata):
                    continue

            # Calculate cosine similarity
            vec_np = np.array(vector)
            similarity = self._cosine_similarity(query_np, vec_np)
            results.append((id, similarity, metadata))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)

        return [
            VectorSearchResult(id=r[0], score=r[1], metadata=r[2])
            for r in results[:limit]
        ]

    async def get(
        self,
        namespace: str,
        id: str,
    ) -> tuple[list[float], dict[str, Any]] | None:
        """Get a vector by ID.

        Args:
            namespace: Namespace for the vector.
            id: Unique identifier for the vector.

        Returns:
            Tuple of (vector, metadata) or None if not found.
        """
        if namespace not in self._store:
            return None

        return self._store[namespace].get(id)

    async def count(self, namespace: str) -> int:
        """Count vectors in a namespace.

        Args:
            namespace: Namespace to count.

        Returns:
            Number of vectors.
        """
        if namespace not in self._store:
            return 0
        return len(self._store[namespace])

    async def clear(self, namespace: str) -> int:
        """Clear all vectors in a namespace.

        Args:
            namespace: Namespace to clear.

        Returns:
            Number of vectors deleted.
        """
        if namespace not in self._store:
            return 0

        count = len(self._store[namespace])
        self._store[namespace] = {}
        return count

    def _cosine_similarity(
        self,
        a: np.ndarray,
        b: np.ndarray,
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(np.dot(a, b) / (norm_a * norm_b))

    def _matches_filter(
        self,
        metadata: dict[str, Any],
        filter_metadata: dict[str, Any],
    ) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_metadata.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True


# Singleton instance
_vector_store: VectorStoreService | None = None


def get_vector_store() -> VectorStoreService:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
