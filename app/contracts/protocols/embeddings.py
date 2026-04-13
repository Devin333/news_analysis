"""Embedding provider protocol."""

from typing import Protocol, Sequence


class EmbeddingProviderProtocol(Protocol):
    """Protocol for embedding providers.

    Embedding providers generate vector representations of text
    that can be used for semantic similarity comparisons.
    """

    @property
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    def dimension(self) -> int:
        """Embedding vector dimension."""
        ...

    @property
    def max_tokens(self) -> int:
        """Maximum tokens per input text."""
        ...

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        ...

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: Input texts to embed.

        Returns:
            List of embedding vectors.
        """
        ...
