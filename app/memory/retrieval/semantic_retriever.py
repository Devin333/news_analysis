"""Semantic Retriever for memory search.

Provides semantic search capabilities for finding similar
topics, judgements, and historical context.
"""

from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import JudgementMemoryDTO, TopicMemoryDTO
from app.vector_store.service import VectorSearchResult, VectorStoreService

if TYPE_CHECKING:
    from app.embeddings.indexing import MemoryIndexer
    from app.memory.repositories.judgement_repository import JudgementRepository
    from app.memory.repositories.topic_memory_repository import TopicMemoryRepository

logger = get_logger(__name__)


# Namespace constants
NS_TOPICS = "topics"
NS_TOPIC_MEMORIES = "topic_memories"
NS_JUDGEMENTS = "judgements"


class SemanticRetriever:
    """Semantic retrieval for memory search.

    Uses embeddings to find similar topics, judgements,
    and historical context.
    """

    def __init__(
        self,
        indexer: "MemoryIndexer",
        vector_store: VectorStoreService,
        topic_memory_repo: "TopicMemoryRepository | None" = None,
        judgement_repo: "JudgementRepository | None" = None,
    ) -> None:
        """Initialize the retriever.

        Args:
            indexer: Memory indexer for generating embeddings.
            vector_store: Vector store for similarity search.
            topic_memory_repo: Optional topic memory repository.
            judgement_repo: Optional judgement repository.
        """
        self._indexer = indexer
        self._vector_store = vector_store
        self._topic_memory_repo = topic_memory_repo
        self._judgement_repo = judgement_repo

    async def retrieve_similar_topics_by_text(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[int, float]]:
        """Find topics similar to a text query.

        Args:
            query: Search query text.
            limit: Maximum number of results.

        Returns:
            List of (topic_id, similarity_score) tuples.
        """
        # Generate query embedding
        query_embedding = await self._indexer.embed_query(query)
        if query_embedding is None:
            return []

        # Search vector store
        results = await self._vector_store.search(
            namespace=NS_TOPICS,
            query_vector=query_embedding,
            limit=limit,
        )

        return [
            (int(r.id), r.score)
            for r in results
        ]

    async def retrieve_similar_judgements(
        self,
        query: str,
        limit: int = 10,
    ) -> list[JudgementMemoryDTO]:
        """Find judgements similar to a text query.

        Args:
            query: Search query text.
            limit: Maximum number of results.

        Returns:
            List of similar JudgementMemoryDTO.
        """
        if self._judgement_repo is None:
            return []

        # Generate query embedding
        query_embedding = await self._indexer.embed_query(query)
        if query_embedding is None:
            return []

        # Search vector store
        results = await self._vector_store.search(
            namespace=NS_JUDGEMENTS,
            query_vector=query_embedding,
            limit=limit,
        )

        # Fetch full judgement records
        judgements: list[JudgementMemoryDTO] = []
        for result in results:
            # ID format: "{target_type}:{target_id}:{judgement_id}"
            parts = result.id.split(":")
            if len(parts) >= 3:
                target_type = parts[0]
                target_id = int(parts[1])
                # Get judgements for this target
                target_judgements = await self._judgement_repo.list_by_target(
                    target_type, target_id, limit=5
                )
                judgements.extend(target_judgements)

        # Deduplicate and limit
        seen_ids: set[int] = set()
        unique_judgements: list[JudgementMemoryDTO] = []
        for j in judgements:
            if j.id and j.id not in seen_ids:
                seen_ids.add(j.id)
                unique_judgements.append(j)
                if len(unique_judgements) >= limit:
                    break

        return unique_judgements

    async def retrieve_related_history_by_query(
        self,
        query: str,
        limit: int = 10,
    ) -> list[TopicMemoryDTO]:
        """Find topic memories related to a query.

        Args:
            query: Search query text.
            limit: Maximum number of results.

        Returns:
            List of related TopicMemoryDTO.
        """
        if self._topic_memory_repo is None:
            return []

        # Generate query embedding
        query_embedding = await self._indexer.embed_query(query)
        if query_embedding is None:
            return []

        # Search vector store
        results = await self._vector_store.search(
            namespace=NS_TOPIC_MEMORIES,
            query_vector=query_embedding,
            limit=limit,
        )

        # Fetch full topic memory records
        memories: list[TopicMemoryDTO] = []
        for result in results:
            topic_id = int(result.id)
            memory = await self._topic_memory_repo.get_by_topic_id(topic_id)
            if memory:
                memories.append(memory)

        return memories

    async def index_topic(
        self,
        topic_id: int,
        title: str,
        summary: str | None = None,
    ) -> bool:
        """Index a topic for semantic search.

        Args:
            topic_id: Topic ID.
            title: Topic title.
            summary: Optional topic summary.

        Returns:
            True if indexed successfully.
        """
        embedding = await self._indexer.index_topic_summary(topic_id, title, summary)
        if embedding is None:
            return False

        await self._vector_store.upsert(
            namespace=NS_TOPICS,
            id=str(topic_id),
            vector=embedding,
            metadata={"title": title},
        )
        return True

    async def index_topic_memory(
        self,
        memory: TopicMemoryDTO,
    ) -> bool:
        """Index a topic memory for semantic search.

        Args:
            memory: Topic memory DTO.

        Returns:
            True if indexed successfully.
        """
        embedding = await self._indexer.index_topic_memory(memory)
        if embedding is None:
            return False

        await self._vector_store.upsert(
            namespace=NS_TOPIC_MEMORIES,
            id=str(memory.topic_id),
            vector=embedding,
            metadata={
                "historical_status": memory.historical_status,
                "current_stage": memory.current_stage,
            },
        )
        return True

    async def index_judgement(
        self,
        judgement: JudgementMemoryDTO,
    ) -> bool:
        """Index a judgement for semantic search.

        Args:
            judgement: Judgement DTO.

        Returns:
            True if indexed successfully.
        """
        embedding = await self._indexer.index_judgement(judgement)
        if embedding is None:
            return False

        # Create unique ID
        judgement_id = f"{judgement.target_type}:{judgement.target_id}:{judgement.id}"

        await self._vector_store.upsert(
            namespace=NS_JUDGEMENTS,
            id=judgement_id,
            vector=embedding,
            metadata={
                "target_type": judgement.target_type,
                "target_id": judgement.target_id,
                "judgement_type": judgement.judgement_type,
                "agent_name": judgement.agent_name,
            },
        )
        return True
