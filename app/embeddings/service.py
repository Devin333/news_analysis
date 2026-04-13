"""Embedding service for text embedding operations."""

import math
from dataclasses import dataclass
from typing import Sequence

from app.bootstrap.logging import get_logger
from app.contracts.protocols.embeddings import EmbeddingProviderProtocol

logger = get_logger(__name__)


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""

    text: str
    embedding: list[float]
    dimension: int
    provider: str


def cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Cosine similarity in range [-1, 1].
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def euclidean_distance(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Compute Euclidean distance between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Euclidean distance (non-negative).
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

    return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))


class EmbeddingService:
    """Service for embedding operations.

    Provides a high-level interface for text embedding and similarity
    computation, abstracting away the underlying provider.
    """

    def __init__(self, provider: EmbeddingProviderProtocol) -> None:
        """Initialize the service.

        Args:
            provider: Embedding provider to use.
        """
        self._provider = provider

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return self._provider.name

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._provider.dimension

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: Text to embed.

        Returns:
            EmbeddingResult with the embedding vector.
        """
        # Truncate if needed
        truncated = self._truncate_text(text)

        embedding = await self._provider.embed(truncated)

        logger.debug(
            f"Embedded text ({len(text)} chars) -> {len(embedding)} dims "
            f"using {self._provider.name}"
        )

        return EmbeddingResult(
            text=truncated,
            embedding=embedding,
            dimension=len(embedding),
            provider=self._provider.name,
        )

    async def embed_texts(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 32,
    ) -> list[EmbeddingResult]:
        """Embed multiple texts.

        Args:
            texts: Texts to embed.
            batch_size: Maximum batch size for API calls.

        Returns:
            List of EmbeddingResults.
        """
        if not texts:
            return []

        # Truncate texts
        truncated = [self._truncate_text(t) for t in texts]

        # Process in batches
        results: list[EmbeddingResult] = []
        for i in range(0, len(truncated), batch_size):
            batch = truncated[i : i + batch_size]
            embeddings = await self._provider.embed_batch(batch)

            for text, embedding in zip(batch, embeddings):
                results.append(
                    EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        dimension=len(embedding),
                        provider=self._provider.name,
                    )
                )

        logger.info(
            f"Embedded {len(texts)} texts in {(len(texts) + batch_size - 1) // batch_size} batches"
        )

        return results

    async def compute_similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """Compute semantic similarity between two texts.

        Args:
            text1: First text.
            text2: Second text.

        Returns:
            Similarity score in range [0, 1].
        """
        results = await self.embed_texts([text1, text2])
        similarity = cosine_similarity(results[0].embedding, results[1].embedding)
        # Normalize to [0, 1] range
        return (similarity + 1) / 2

    async def compute_similarity_to_many(
        self,
        query: str,
        candidates: Sequence[str],
    ) -> list[tuple[int, float]]:
        """Compute similarity of query to multiple candidates.

        Args:
            query: Query text.
            candidates: Candidate texts to compare against.

        Returns:
            List of (index, similarity) tuples, sorted by similarity descending.
        """
        if not candidates:
            return []

        # Embed query and candidates together
        all_texts = [query] + list(candidates)
        results = await self.embed_texts(all_texts)

        query_embedding = results[0].embedding
        similarities: list[tuple[int, float]] = []

        for i, result in enumerate(results[1:]):
            sim = cosine_similarity(query_embedding, result.embedding)
            # Normalize to [0, 1]
            normalized = (sim + 1) / 2
            similarities.append((i, normalized))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities

    async def find_most_similar(
        self,
        query: str,
        candidates: Sequence[str],
        *,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> list[tuple[int, str, float]]:
        """Find most similar candidates to query.

        Args:
            query: Query text.
            candidates: Candidate texts.
            top_k: Maximum number of results.
            min_similarity: Minimum similarity threshold.

        Returns:
            List of (index, text, similarity) tuples.
        """
        similarities = await self.compute_similarity_to_many(query, candidates)

        results: list[tuple[int, str, float]] = []
        for idx, sim in similarities[:top_k]:
            if sim >= min_similarity:
                results.append((idx, candidates[idx], sim))

        return results

    def _truncate_text(self, text: str, max_chars: int = 8000) -> str:
        """Truncate text to fit within token limits.

        Simple character-based truncation. For more accurate truncation,
        use a tokenizer.

        Args:
            text: Text to truncate.
            max_chars: Maximum characters (rough approximation of tokens).

        Returns:
            Truncated text.
        """
        if len(text) <= max_chars:
            return text

        # Truncate and add indicator
        return text[: max_chars - 3] + "..."
