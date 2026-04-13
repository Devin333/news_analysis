"""Unit tests for embedding providers and service."""

import math

import pytest

from app.embeddings.provider import (
    DummyEmbeddingProvider,
    EmbeddingProviderFactory,
)
from app.embeddings.service import (
    EmbeddingService,
    cosine_similarity,
    euclidean_distance,
)


class TestDummyEmbeddingProvider:
    """Tests for DummyEmbeddingProvider."""

    @pytest.mark.asyncio
    async def test_embed_returns_correct_dimension(self) -> None:
        """Should return embedding with correct dimension."""
        provider = DummyEmbeddingProvider(dimension=384)
        embedding = await provider.embed("test text")
        assert len(embedding) == 384

    @pytest.mark.asyncio
    async def test_embed_is_deterministic(self) -> None:
        """Same text should produce same embedding."""
        provider = DummyEmbeddingProvider()
        emb1 = await provider.embed("hello world")
        emb2 = await provider.embed("hello world")
        assert emb1 == emb2

    @pytest.mark.asyncio
    async def test_embed_different_texts_differ(self) -> None:
        """Different texts should produce different embeddings."""
        provider = DummyEmbeddingProvider()
        emb1 = await provider.embed("hello world")
        emb2 = await provider.embed("goodbye world")
        assert emb1 != emb2

    @pytest.mark.asyncio
    async def test_embed_empty_text(self) -> None:
        """Empty text should return zero vector."""
        provider = DummyEmbeddingProvider(dimension=10)
        embedding = await provider.embed("")
        assert embedding == [0.0] * 10

    @pytest.mark.asyncio
    async def test_embed_is_normalized(self) -> None:
        """Embedding should be normalized to unit length."""
        provider = DummyEmbeddingProvider()
        embedding = await provider.embed("test text")
        norm = math.sqrt(sum(v * v for v in embedding))
        assert norm == pytest.approx(1.0, abs=0.001)

    @pytest.mark.asyncio
    async def test_embed_batch(self) -> None:
        """Should embed multiple texts."""
        provider = DummyEmbeddingProvider()
        texts = ["text one", "text two", "text three"]
        embeddings = await provider.embed_batch(texts)
        assert len(embeddings) == 3
        assert all(len(e) == provider.dimension for e in embeddings)

    def test_provider_properties(self) -> None:
        """Should have correct properties."""
        provider = DummyEmbeddingProvider(dimension=512)
        assert provider.name == "dummy"
        assert provider.dimension == 512
        assert provider.max_tokens == 8192


class TestEmbeddingProviderFactory:
    """Tests for EmbeddingProviderFactory."""

    def test_create_dummy_provider(self) -> None:
        """Should create dummy provider."""
        provider = EmbeddingProviderFactory.create("dummy", dimension=256)
        assert provider.name == "dummy"
        assert provider.dimension == 256

    def test_create_unknown_provider_raises(self) -> None:
        """Should raise for unknown provider type."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            EmbeddingProviderFactory.create("unknown")


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self) -> None:
        """Identical vectors should have similarity 1.0."""
        vec = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_opposite_vectors(self) -> None:
        """Opposite vectors should have similarity -1.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(-1.0)

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors should have similarity 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_zero_vector(self) -> None:
        """Zero vector should return 0.0."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        assert cosine_similarity(vec1, vec2) == 0.0

    def test_dimension_mismatch_raises(self) -> None:
        """Should raise for mismatched dimensions."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError, match="dimensions must match"):
            cosine_similarity(vec1, vec2)


class TestEuclideanDistance:
    """Tests for euclidean_distance function."""

    def test_identical_vectors(self) -> None:
        """Identical vectors should have distance 0.0."""
        vec = [1.0, 2.0, 3.0]
        assert euclidean_distance(vec, vec) == 0.0

    def test_known_distance(self) -> None:
        """Should compute correct distance."""
        vec1 = [0.0, 0.0]
        vec2 = [3.0, 4.0]
        assert euclidean_distance(vec1, vec2) == pytest.approx(5.0)

    def test_dimension_mismatch_raises(self) -> None:
        """Should raise for mismatched dimensions."""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]
        with pytest.raises(ValueError, match="dimensions must match"):
            euclidean_distance(vec1, vec2)


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    @pytest.mark.asyncio
    async def test_embed_text(self) -> None:
        """Should embed single text."""
        provider = DummyEmbeddingProvider(dimension=128)
        service = EmbeddingService(provider)

        result = await service.embed_text("test text")

        assert result.text == "test text"
        assert len(result.embedding) == 128
        assert result.dimension == 128
        assert result.provider == "dummy"

    @pytest.mark.asyncio
    async def test_embed_texts(self) -> None:
        """Should embed multiple texts."""
        provider = DummyEmbeddingProvider(dimension=128)
        service = EmbeddingService(provider)

        results = await service.embed_texts(["text one", "text two"])

        assert len(results) == 2
        assert results[0].text == "text one"
        assert results[1].text == "text two"

    @pytest.mark.asyncio
    async def test_embed_texts_empty(self) -> None:
        """Should handle empty list."""
        provider = DummyEmbeddingProvider()
        service = EmbeddingService(provider)

        results = await service.embed_texts([])

        assert results == []

    @pytest.mark.asyncio
    async def test_compute_similarity(self) -> None:
        """Should compute similarity between texts."""
        provider = DummyEmbeddingProvider()
        service = EmbeddingService(provider)

        # Same text should have high similarity
        sim = await service.compute_similarity("hello world", "hello world")
        assert sim == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_compute_similarity_to_many(self) -> None:
        """Should compute similarity to multiple candidates."""
        provider = DummyEmbeddingProvider()
        service = EmbeddingService(provider)

        query = "machine learning"
        candidates = ["deep learning", "web development", "machine learning"]

        results = await service.compute_similarity_to_many(query, candidates)

        assert len(results) == 3
        # Results should be sorted by similarity descending
        assert results[0][1] >= results[1][1] >= results[2][1]
        # Exact match should be first
        assert results[0][0] == 2  # "machine learning" index

    @pytest.mark.asyncio
    async def test_find_most_similar(self) -> None:
        """Should find most similar candidates."""
        provider = DummyEmbeddingProvider()
        service = EmbeddingService(provider)

        query = "python programming"
        candidates = ["java programming", "python coding", "web design"]

        results = await service.find_most_similar(query, candidates, top_k=2)

        assert len(results) <= 2
        # Each result should be (index, text, similarity)
        assert all(len(r) == 3 for r in results)

    @pytest.mark.asyncio
    async def test_find_most_similar_with_threshold(self) -> None:
        """Should filter by minimum similarity."""
        provider = DummyEmbeddingProvider()
        service = EmbeddingService(provider)

        query = "unique query"
        candidates = ["completely different"]

        results = await service.find_most_similar(
            query, candidates, min_similarity=0.99
        )

        # Should filter out low similarity results
        assert len(results) == 0 or results[0][2] >= 0.99

    def test_service_properties(self) -> None:
        """Should expose provider properties."""
        provider = DummyEmbeddingProvider(dimension=256)
        service = EmbeddingService(provider)

        assert service.provider_name == "dummy"
        assert service.dimension == 256

    @pytest.mark.asyncio
    async def test_truncate_long_text(self) -> None:
        """Should truncate very long text."""
        provider = DummyEmbeddingProvider()
        service = EmbeddingService(provider)

        long_text = "a" * 10000
        result = await service.embed_text(long_text)

        # Should be truncated
        assert len(result.text) < 10000
        assert result.text.endswith("...")
