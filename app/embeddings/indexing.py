"""Embedding indexing for memory retrieval.

Provides functions to build embeddings for various memory objects
for semantic search.
"""

from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.memory import JudgementMemoryDTO, TopicMemoryDTO, TopicSnapshotDTO
    from app.contracts.dto.normalized_item import NormalizedItemDTO
    from app.contracts.protocols.embeddings import EmbeddingProviderProtocol

logger = get_logger(__name__)


class MemoryIndexer:
    """Index memory objects for semantic search."""

    def __init__(
        self,
        embedding_provider: "EmbeddingProviderProtocol",
    ) -> None:
        """Initialize the indexer.

        Args:
            embedding_provider: Provider for generating embeddings.
        """
        self._provider = embedding_provider

    async def index_normalized_item(
        self,
        item: "NormalizedItemDTO",
    ) -> list[float] | None:
        """Generate embedding for a normalized item.

        Uses title + excerpt for embedding.

        Args:
            item: The normalized item.

        Returns:
            Embedding vector or None if failed.
        """
        text = self._build_item_text(item)
        if not text:
            return None

        try:
            embedding = await self._provider.embed_text(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed item {item.id}: {e}")
            return None

    async def index_topic_summary(
        self,
        topic_id: int,
        title: str,
        summary: str | None,
    ) -> list[float] | None:
        """Generate embedding for a topic summary.

        Args:
            topic_id: Topic ID for logging.
            title: Topic title.
            summary: Topic summary.

        Returns:
            Embedding vector or None if failed.
        """
        text = title
        if summary:
            text = f"{title}\n{summary}"

        try:
            embedding = await self._provider.embed_text(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed topic {topic_id}: {e}")
            return None

    async def index_topic_memory(
        self,
        memory: "TopicMemoryDTO",
    ) -> list[float] | None:
        """Generate embedding for topic memory history summary.

        Args:
            memory: Topic memory DTO.

        Returns:
            Embedding vector or None if failed.
        """
        if not memory.history_summary:
            return None

        try:
            embedding = await self._provider.embed_text(memory.history_summary)
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed topic memory {memory.topic_id}: {e}")
            return None

    async def index_judgement(
        self,
        judgement: "JudgementMemoryDTO",
    ) -> list[float] | None:
        """Generate embedding for a judgement.

        Args:
            judgement: Judgement DTO.

        Returns:
            Embedding vector or None if failed.
        """
        text = f"{judgement.judgement_type}: {judgement.judgement}"

        try:
            embedding = await self._provider.embed_text(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed judgement {judgement.id}: {e}")
            return None

    async def index_snapshot(
        self,
        snapshot: "TopicSnapshotDTO",
    ) -> list[float] | None:
        """Generate embedding for a topic snapshot.

        Args:
            snapshot: Topic snapshot DTO.

        Returns:
            Embedding vector or None if failed.
        """
        parts = []
        if snapshot.summary:
            parts.append(snapshot.summary)
        if snapshot.why_it_matters:
            parts.append(snapshot.why_it_matters)
        if snapshot.system_judgement:
            parts.append(snapshot.system_judgement)

        if not parts:
            return None

        text = "\n".join(parts)

        try:
            embedding = await self._provider.embed_text(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed snapshot {snapshot.id}: {e}")
            return None

    async def embed_query(self, query: str) -> list[float] | None:
        """Generate embedding for a search query.

        Args:
            query: Search query text.

        Returns:
            Embedding vector or None if failed.
        """
        try:
            return await self._provider.embed_text(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return None

    def _build_item_text(self, item: "NormalizedItemDTO") -> str:
        """Build text representation of an item for embedding."""
        parts = []

        if item.title:
            parts.append(item.title)

        if item.excerpt:
            # Limit excerpt length
            excerpt = item.excerpt[:1000]
            parts.append(excerpt)

        return "\n".join(parts)
