"""Semantic search implementation using vector embeddings."""

from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.search import SearchContentType, SearchResultItemDTO
from app.contracts.protocols.search import SemanticSearchProtocol

if TYPE_CHECKING:
    from app.contracts.protocols.embeddings import EmbeddingProviderProtocol
    from app.vector_store.service import VectorStoreService

logger = get_logger(__name__)


class SemanticSearch(SemanticSearchProtocol):
    """Semantic search using vector embeddings.

    Supports:
    - Query embedding
    - Similar topic/item/memory search
    - Hybrid query support
    """

    def __init__(
        self,
        embedding_provider: "EmbeddingProviderProtocol | None" = None,
        vector_store: "VectorStoreService | None" = None,
    ) -> None:
        """Initialize semantic search.

        Args:
            embedding_provider: Provider for text embeddings
            vector_store: Vector store service
        """
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        min_score: float = 0.0,
        content_types: list[SearchContentType] | None = None,
    ) -> list[SearchResultItemDTO]:
        """Execute semantic search.

        Args:
            query: Search query string
            top_k: Number of results
            min_score: Minimum similarity score
            content_types: Content types to search

        Returns:
            List of search results
        """
        if not self._embedding_provider or not self._vector_store:
            logger.warning("Semantic search not configured")
            return []

        try:
            # Get query embedding
            query_embedding = await self._embedding_provider.embed_query(query)

            # Search vector store
            results: list[SearchResultItemDTO] = []

            # Search topics
            if not content_types or SearchContentType.TOPIC in content_types:
                topic_results = await self._search_topics(
                    query_embedding, top_k, min_score
                )
                results.extend(topic_results)

            # Search items
            if not content_types or SearchContentType.ITEM in content_types:
                item_results = await self._search_items(
                    query_embedding, top_k, min_score
                )
                results.extend(item_results)

            # Search entities
            if content_types and SearchContentType.ENTITY in content_types:
                entity_results = await self._search_entities(
                    query_embedding, top_k, min_score
                )
                results.extend(entity_results)

            # Sort by score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    async def _search_topics(
        self,
        query_embedding: list[float],
        top_k: int,
        min_score: float,
    ) -> list[SearchResultItemDTO]:
        """Search topics by embedding similarity.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            min_score: Minimum score

        Returns:
            List of topic results
        """
        if not self._vector_store:
            return []

        try:
            # Query vector store for topics
            matches = await self._vector_store.query(
                query_embedding,
                collection="topics",
                top_k=top_k,
                min_score=min_score,
            )

            return [
                SearchResultItemDTO(
                    id=int(match["id"]),
                    content_type=SearchContentType.TOPIC,
                    score=match["score"],
                    title=match.get("metadata", {}).get("title", ""),
                    summary=match.get("metadata", {}).get("summary"),
                    board_type=match.get("metadata", {}).get("board_type"),
                    semantic_score=match["score"],
                    metadata=match.get("metadata", {}),
                )
                for match in matches
            ]
        except Exception as e:
            logger.error(f"Topic semantic search failed: {e}")
            return []

    async def _search_items(
        self,
        query_embedding: list[float],
        top_k: int,
        min_score: float,
    ) -> list[SearchResultItemDTO]:
        """Search items by embedding similarity.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            min_score: Minimum score

        Returns:
            List of item results
        """
        if not self._vector_store:
            return []

        try:
            matches = await self._vector_store.query(
                query_embedding,
                collection="items",
                top_k=top_k,
                min_score=min_score,
            )

            return [
                SearchResultItemDTO(
                    id=int(match["id"]),
                    content_type=SearchContentType.ITEM,
                    score=match["score"],
                    title=match.get("metadata", {}).get("title", ""),
                    excerpt=match.get("metadata", {}).get("excerpt"),
                    semantic_score=match["score"],
                    metadata=match.get("metadata", {}),
                )
                for match in matches
            ]
        except Exception as e:
            logger.error(f"Item semantic search failed: {e}")
            return []

    async def _search_entities(
        self,
        query_embedding: list[float],
        top_k: int,
        min_score: float,
    ) -> list[SearchResultItemDTO]:
        """Search entities by embedding similarity.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            min_score: Minimum score

        Returns:
            List of entity results
        """
        if not self._vector_store:
            return []

        try:
            matches = await self._vector_store.query(
                query_embedding,
                collection="entities",
                top_k=top_k,
                min_score=min_score,
            )

            return [
                SearchResultItemDTO(
                    id=int(match["id"]),
                    content_type=SearchContentType.ENTITY,
                    score=match["score"],
                    title=match.get("metadata", {}).get("name", ""),
                    summary=match.get("metadata", {}).get("description"),
                    semantic_score=match["score"],
                    metadata=match.get("metadata", {}),
                )
                for match in matches
            ]
        except Exception as e:
            logger.error(f"Entity semantic search failed: {e}")
            return []

    async def get_similar(
        self,
        item_id: int,
        content_type: str,
        *,
        top_k: int = 10,
    ) -> list[SearchResultItemDTO]:
        """Find similar items by ID.

        Args:
            item_id: Source item ID
            content_type: Content type
            top_k: Number of results

        Returns:
            List of similar items
        """
        if not self._vector_store:
            return []

        try:
            # Get embedding for the source item
            collection = f"{content_type}s"  # topics, items, entities
            source_embedding = await self._vector_store.get_embedding(
                item_id, collection
            )

            if not source_embedding:
                return []

            # Find similar
            matches = await self._vector_store.query(
                source_embedding,
                collection=collection,
                top_k=top_k + 1,  # +1 to exclude self
                min_score=0.0,
            )

            # Filter out self
            results = []
            for match in matches:
                if int(match["id"]) != item_id:
                    results.append(
                        SearchResultItemDTO(
                            id=int(match["id"]),
                            content_type=SearchContentType(content_type),
                            score=match["score"],
                            title=match.get("metadata", {}).get("title", ""),
                            semantic_score=match["score"],
                            metadata=match.get("metadata", {}),
                        )
                    )

            return results[:top_k]

        except Exception as e:
            logger.error(f"Similar search failed: {e}")
            return []

    async def search_with_filters(
        self,
        query: str,
        *,
        board_filter: list[str] | None = None,
        tags_filter: list[str] | None = None,
        top_k: int = 20,
        min_score: float = 0.0,
    ) -> list[SearchResultItemDTO]:
        """Semantic search with metadata filters.

        Args:
            query: Search query
            board_filter: Board types to include
            tags_filter: Tags to include
            top_k: Number of results
            min_score: Minimum score

        Returns:
            List of filtered results
        """
        if not self._embedding_provider or not self._vector_store:
            return []

        try:
            query_embedding = await self._embedding_provider.embed_query(query)

            # Build filter
            metadata_filter = {}
            if board_filter:
                metadata_filter["board_type"] = {"$in": board_filter}
            if tags_filter:
                metadata_filter["tags"] = {"$containsAny": tags_filter}

            matches = await self._vector_store.query(
                query_embedding,
                collection="topics",
                top_k=top_k,
                min_score=min_score,
                filter=metadata_filter if metadata_filter else None,
            )

            return [
                SearchResultItemDTO(
                    id=int(match["id"]),
                    content_type=SearchContentType.TOPIC,
                    score=match["score"],
                    title=match.get("metadata", {}).get("title", ""),
                    summary=match.get("metadata", {}).get("summary"),
                    board_type=match.get("metadata", {}).get("board_type"),
                    semantic_score=match["score"],
                    metadata=match.get("metadata", {}),
                )
                for match in matches
            ]

        except Exception as e:
            logger.error(f"Filtered semantic search failed: {e}")
            return []
