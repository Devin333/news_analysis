"""Embedding providers implementation.

This module provides embedding provider implementations that can be
used for semantic similarity in topic clustering.
"""

import hashlib
import math
from abc import ABC, abstractmethod
from typing import Sequence

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        ...

    @property
    def max_tokens(self) -> int:
        """Maximum tokens per input text."""
        return 8192

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Default implementation calls embed() for each text.
        Subclasses can override for batch optimization.
        """
        return [await self.embed(text) for text in texts]


class DummyEmbeddingProvider(BaseEmbeddingProvider):
    """Dummy embedding provider for testing.

    Generates deterministic pseudo-embeddings based on text hash.
    Useful for testing without requiring an actual embedding model.
    """

    def __init__(self, dimension: int = 384) -> None:
        """Initialize dummy provider.

        Args:
            dimension: Embedding dimension (default 384 for compatibility).
        """
        self._dimension = dimension

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """Generate deterministic pseudo-embedding from text hash.

        The embedding is normalized to unit length.
        """
        if not text:
            return [0.0] * self._dimension

        # Use SHA256 hash to generate deterministic values
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()

        # Expand hash to fill dimension
        embedding: list[float] = []
        for i in range(self._dimension):
            # Use different parts of hash for each dimension
            byte_idx = i % len(hash_bytes)
            # Convert to float in range [-1, 1]
            value = (hash_bytes[byte_idx] / 127.5) - 1.0
            # Add some variation based on position
            value = value * math.cos(i * 0.1)
            embedding.append(value)

        # Normalize to unit length
        norm = math.sqrt(sum(v * v for v in embedding))
        if norm > 0:
            embedding = [v / norm for v in embedding]

        return embedding


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using sentence-transformers.

    Requires sentence-transformers package to be installed.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        """Initialize local provider.

        Args:
            model_name: Sentence transformer model name.
            device: Device to run model on (cpu/cuda).
        """
        self._model_name = model_name
        self._device = device
        self._model = None
        self._dimension_cache: int | None = None

    @property
    def name(self) -> str:
        return f"local:{self._model_name}"

    @property
    def dimension(self) -> int:
        if self._dimension_cache is None:
            # Default dimensions for common models
            default_dims = {
                "all-MiniLM-L6-v2": 384,
                "all-mpnet-base-v2": 768,
                "paraphrase-MiniLM-L6-v2": 384,
            }
            self._dimension_cache = default_dims.get(self._model_name, 384)
        return self._dimension_cache

    def _get_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self._model_name, device=self._device)
                self._dimension_cache = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded embedding model: {self._model_name}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for LocalEmbeddingProvider. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using local model."""
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for batch using local model."""
        model = self._get_model()
        embeddings = model.encode(list(texts), convert_to_numpy=True)
        return [e.tolist() for e in embeddings]


class APIEmbeddingProvider(BaseEmbeddingProvider):
    """API-based embedding provider.

    Supports OpenAI-compatible embedding APIs.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        dimension: int = 1536,
    ) -> None:
        """Initialize API provider.

        Args:
            api_key: API key for authentication.
            model: Model name to use.
            base_url: API base URL.
            dimension: Expected embedding dimension.
        """
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._dimension = dimension

    @property
    def name(self) -> str:
        return f"api:{self._model}"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> list[float]:
        """Generate embedding via API call."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "input": text,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for batch via API call."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "input": list(texts),
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            # Sort by index to maintain order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in sorted_data]


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    @staticmethod
    def create(
        provider_type: str = "dummy",
        **kwargs,
    ) -> BaseEmbeddingProvider:
        """Create an embedding provider.

        Args:
            provider_type: Type of provider (dummy, local, api).
            **kwargs: Provider-specific arguments.

        Returns:
            Configured embedding provider.

        Raises:
            ValueError: If provider type is unknown.
        """
        if provider_type == "dummy":
            return DummyEmbeddingProvider(**kwargs)
        elif provider_type == "local":
            return LocalEmbeddingProvider(**kwargs)
        elif provider_type == "api":
            return APIEmbeddingProvider(**kwargs)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
