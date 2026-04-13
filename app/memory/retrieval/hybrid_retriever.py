"""Hybrid Retriever combining structured and semantic retrieval.

Provides a unified interface for retrieving historical context
using both structured queries and semantic search.
"""

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import (
    EntityMemoryDTO,
    JudgementMemoryDTO,
    MemoryRetrievalResultDTO,
    TimelinePointDTO,
    TopicMemoryDTO,
    TopicSnapshotDTO,
)
from app.memory.retrieval.policies import RetrievalPolicy, get_policy

if TYPE_CHECKING:
    from app.memory.retrieval.semantic_retriever import SemanticRetriever
    from app.memory.retrieval.service import MemoryRetrievalService

logger = get_logger(__name__)


@dataclass
class HybridRetrievalResult:
    """Result from hybrid retrieval."""

    # Core memory
    topic_memory: TopicMemoryDTO | None = None
    snapshots: list[TopicSnapshotDTO] = field(default_factory=list)
    timeline: list[TimelinePointDTO] = field(default_factory=list)

    # Judgements
    judgements: list[JudgementMemoryDTO] = field(default_factory=list)

    # Entity context
    entity_memories: list[EntityMemoryDTO] = field(default_factory=list)

    # Related topics
    related_topics: list[int] = field(default_factory=list)
    similar_topics_by_embedding: list[tuple[int, float]] = field(default_factory=list)

    # Similar historical cases
    similar_historical_cases: list[TopicMemoryDTO] = field(default_factory=list)

    # Metadata
    retrieval_time_ms: float = 0.0
    policy_used: str = ""


class HybridRetriever:
    """Hybrid retriever combining structured and semantic search.

    Combines:
    - Topic ID exact match
    - Entity overlap
    - Time range filtering
    - Tags overlap
    - Embedding similarity
    """

    def __init__(
        self,
        structured_retriever: "MemoryRetrievalService",
        semantic_retriever: "SemanticRetriever | None" = None,
    ) -> None:
        """Initialize the hybrid retriever.

        Args:
            structured_retriever: Structured memory retrieval service.
            semantic_retriever: Optional semantic retriever.
        """
        self._structured = structured_retriever
        self._semantic = semantic_retriever

    async def retrieve(
        self,
        topic_id: int,
        policy: RetrievalPolicy | str | None = None,
    ) -> HybridRetrievalResult:
        """Retrieve historical context using hybrid approach.

        Args:
            topic_id: The topic ID.
            policy: Retrieval policy or mode name.

        Returns:
            HybridRetrievalResult with all retrieved data.
        """
        start = time.time()

        # Get policy
        if policy is None:
            policy = get_policy("topic_context")
        elif isinstance(policy, str):
            policy = get_policy(policy)

        result = HybridRetrievalResult(policy_used=policy.mode)

        # Structured retrieval
        if policy.include_topic_memory:
            result.topic_memory = await self._structured._topic_memory_repo.get_by_topic_id(topic_id)

        if policy.include_snapshots:
            result.snapshots = await self._structured._topic_memory_repo.list_snapshots(
                topic_id, limit=policy.max_snapshots
            )

        if policy.include_timeline:
            timeline_events = await self._structured._timeline_repo.list_by_topic(
                topic_id, limit=policy.max_timeline_events
            )
            result.timeline = [
                TimelinePointDTO(
                    event_time=e.event_time,
                    event_type=e.event_type,
                    title=e.title,
                    description=e.description,
                    source_item_id=e.source_item_id,
                    source_type=e.source_type,
                    importance_score=e.importance_score,
                    metadata=e.metadata,
                )
                for e in timeline_events
            ]

            # Filter by importance if specified
            if policy.min_importance_score > 0:
                result.timeline = [
                    e for e in result.timeline
                    if e.importance_score >= policy.min_importance_score
                ]

            # Filter by event types if specified
            if policy.timeline_event_types:
                result.timeline = [
                    e for e in result.timeline
                    if e.event_type in policy.timeline_event_types
                ]

        if policy.include_judgements:
            result.judgements = await self._structured._judgement_repo.list_by_target(
                "topic", topic_id, limit=policy.max_judgements
            )

            # Filter by judgement types if specified
            if policy.judgement_types:
                result.judgements = [
                    j for j in result.judgements
                    if j.judgement_type in policy.judgement_types
                ]

        if policy.include_related_topics:
            result.related_topics = await self._structured.retrieve_related_topics(
                topic_id, limit=policy.max_related_topics
            )

        # Semantic retrieval
        if policy.include_semantic_search and self._semantic:
            # Get similar topics by embedding
            query = policy.semantic_query
            if not query and result.topic_memory and result.topic_memory.history_summary:
                query = result.topic_memory.history_summary

            if query:
                result.similar_topics_by_embedding = await self._semantic.retrieve_similar_topics_by_text(
                    query, limit=policy.max_semantic_results
                )

                # Get similar historical cases
                result.similar_historical_cases = await self._semantic.retrieve_related_history_by_query(
                    query, limit=policy.max_semantic_results
                )

        result.retrieval_time_ms = (time.time() - start) * 1000
        logger.info(
            f"Hybrid retrieval for topic {topic_id} completed in {result.retrieval_time_ms:.2f}ms "
            f"(policy: {policy.mode})"
        )

        return result

    async def retrieve_for_historian(
        self,
        topic_id: int,
        query: str | None = None,
    ) -> HybridRetrievalResult:
        """Retrieve context optimized for Historian agent.

        Args:
            topic_id: The topic ID.
            query: Optional semantic query.

        Returns:
            HybridRetrievalResult with historian-focused data.
        """
        policy = get_policy("historian")
        if query:
            policy.semantic_query = query

        return await self.retrieve(topic_id, policy)

    async def retrieve_for_analyst(
        self,
        topic_id: int,
    ) -> HybridRetrievalResult:
        """Retrieve context optimized for Analyst agent.

        Args:
            topic_id: The topic ID.

        Returns:
            HybridRetrievalResult with analyst-focused data.
        """
        return await self.retrieve(topic_id, get_policy("analyst"))

    async def retrieve_quick(
        self,
        topic_id: int,
    ) -> HybridRetrievalResult:
        """Quick retrieval with minimal data.

        Args:
            topic_id: The topic ID.

        Returns:
            HybridRetrievalResult with minimal data.
        """
        return await self.retrieve(topic_id, get_policy("quick"))

    async def retrieve_full(
        self,
        topic_id: int,
        query: str | None = None,
    ) -> HybridRetrievalResult:
        """Full retrieval with all available data.

        Args:
            topic_id: The topic ID.
            query: Optional semantic query.

        Returns:
            HybridRetrievalResult with all data.
        """
        policy = get_policy("full")
        if query:
            policy.semantic_query = query

        return await self.retrieve(topic_id, policy)

    def to_memory_retrieval_result(
        self,
        result: HybridRetrievalResult,
    ) -> MemoryRetrievalResultDTO:
        """Convert hybrid result to standard MemoryRetrievalResultDTO.

        Args:
            result: Hybrid retrieval result.

        Returns:
            MemoryRetrievalResultDTO.
        """
        return MemoryRetrievalResultDTO(
            topic_memory=result.topic_memory,
            snapshots=result.snapshots,
            timeline=result.timeline,
            entity_memories=result.entity_memories,
            related_topics=result.related_topics,
            judgements=result.judgements,
            retrieval_time_ms=result.retrieval_time_ms,
        )
