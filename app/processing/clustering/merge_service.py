"""Topic merge service for clustering decisions.

This module provides the main service for deciding whether to merge
an item into an existing topic or create a new topic.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.topic import TopicReadDTO
from app.contracts.protocols.embeddings import EmbeddingProviderProtocol
from app.processing.clustering.candidate_retriever import (
    CandidateConfig,
    CandidateRetriever,
)
from app.processing.clustering.merge_scorer import (
    ItemContext,
    MergeScorer,
    MergeWeights,
    TopicContext,
)
from app.processing.clustering.policies import (
    MergeDecision,
    MergePolicy,
    PolicyResult,
    get_policy,
)
from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)


class MergeAction(StrEnum):
    """Action to take for an item."""

    CREATE_NEW = "create_new"  # Create a new topic
    MERGE_INTO = "merge_into"  # Merge into existing topic
    SKIP = "skip"  # Skip processing (e.g., duplicate)


@dataclass
class MergeResult:
    """Result of merge decision."""

    action: MergeAction
    target_topic_id: int | None
    confidence: float
    rationale: str
    policy_result: PolicyResult | None = None
    candidate_count: int = 0
    processing_time_ms: float = 0.0


class MergeService:
    """Service for topic merge decisions.

    Orchestrates the full merge decision pipeline:
    1. Retrieve candidate topics
    2. Score candidates
    3. Apply merge policy
    4. Return decision
    """

    def __init__(
        self,
        topic_repo: TopicRepository,
        *,
        embedding_provider: EmbeddingProviderProtocol | None = None,
        policy_name: str = "default",
        candidate_config: CandidateConfig | None = None,
        merge_weights: MergeWeights | None = None,
        use_embedding: bool = False,
    ) -> None:
        """Initialize the merge service.

        Args:
            topic_repo: Repository for topic operations.
            embedding_provider: Optional embedding provider.
            policy_name: Name of merge policy to use.
            candidate_config: Configuration for candidate retrieval.
            merge_weights: Weights for merge scoring.
            use_embedding: Whether to use embedding similarity.
        """
        self._topic_repo = topic_repo
        self._embedding_provider = embedding_provider
        self._policy = get_policy(policy_name)
        self._use_embedding = use_embedding and embedding_provider is not None

        self._retriever = CandidateRetriever(
            topic_repo,
            config=candidate_config,
        )

        self._scorer = MergeScorer(
            weights=merge_weights,
            embedding_provider=embedding_provider,
        )

    async def resolve_for_item(
        self,
        item: NormalizedItemDTO,
        *,
        board_type: BoardType | None = None,
    ) -> MergeResult:
        """Resolve merge decision for an item.

        Args:
            item: The normalized item to process.
            board_type: Optional board type override.

        Returns:
            MergeResult with action and details.
        """
        import time

        start_time = time.perf_counter()

        # Step 1: Retrieve candidates
        candidate_result = await self._retriever.find_candidates(
            item,
            board_type=board_type,
        )

        if not candidate_result.candidates:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"No candidates found for item '{item.title[:50]}...', creating new topic")
            return MergeResult(
                action=MergeAction.CREATE_NEW,
                target_topic_id=None,
                confidence=1.0,
                rationale="No candidate topics found",
                candidate_count=0,
                processing_time_ms=elapsed_ms,
            )

        # Step 2: Build contexts and score
        item_context = self._build_item_context(item)
        topic_contexts = await self._build_topic_contexts(candidate_result.candidates)

        score_results = await self._scorer.score_candidates(
            item_context,
            topic_contexts,
            use_embedding=self._use_embedding,
        )

        # Step 3: Apply policy
        policy_result = self._policy.evaluate(score_results)

        # Step 4: Determine action
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if policy_result.decision == MergeDecision.LIKELY_MERGE:
            logger.info(
                f"Merge item '{item.title[:50]}...' into topic {policy_result.target_topic_id} "
                f"(confidence={policy_result.confidence:.2f})"
            )
            return MergeResult(
                action=MergeAction.MERGE_INTO,
                target_topic_id=policy_result.target_topic_id,
                confidence=policy_result.confidence,
                rationale=policy_result.reason,
                policy_result=policy_result,
                candidate_count=len(candidate_result.candidates),
                processing_time_ms=elapsed_ms,
            )

        elif policy_result.decision == MergeDecision.MUST_CREATE:
            logger.info(f"Create new topic for item '{item.title[:50]}...'")
            return MergeResult(
                action=MergeAction.CREATE_NEW,
                target_topic_id=None,
                confidence=policy_result.confidence,
                rationale=policy_result.reason,
                policy_result=policy_result,
                candidate_count=len(candidate_result.candidates),
                processing_time_ms=elapsed_ms,
            )

        elif policy_result.decision == MergeDecision.UNCERTAIN:
            # For uncertain cases, default to creating new topic
            # In future, could queue for manual review
            logger.info(
                f"Uncertain merge for item '{item.title[:50]}...', creating new topic"
            )
            return MergeResult(
                action=MergeAction.CREATE_NEW,
                target_topic_id=None,
                confidence=policy_result.confidence,
                rationale=f"Uncertain: {policy_result.reason}",
                policy_result=policy_result,
                candidate_count=len(candidate_result.candidates),
                processing_time_ms=elapsed_ms,
            )

        else:  # DO_NOT_MERGE
            logger.info(f"Do not merge item '{item.title[:50]}...', creating new topic")
            return MergeResult(
                action=MergeAction.CREATE_NEW,
                target_topic_id=None,
                confidence=policy_result.confidence,
                rationale=policy_result.reason,
                policy_result=policy_result,
                candidate_count=len(candidate_result.candidates),
                processing_time_ms=elapsed_ms,
            )

    def _build_item_context(self, item: NormalizedItemDTO) -> ItemContext:
        """Build ItemContext from NormalizedItemDTO."""
        return ItemContext(
            title=item.title,
            summary=item.excerpt,
            tags=item.tags or [],
            published_at=item.published_at,
            source_id=item.source_id,
            entities=[],  # TODO: Extract entities
            content_type=item.content_type.value if item.content_type else None,
            board_type=item.board_type_candidate.value if item.board_type_candidate else None,
        )

    async def _build_topic_contexts(
        self,
        candidates: list,
    ) -> list[TopicContext]:
        """Build TopicContext list from candidates."""
        contexts: list[TopicContext] = []

        for candidate in candidates:
            # Get full topic details
            topic = await self._topic_repo.get_by_id(candidate.topic_id)
            if topic is None:
                continue

            # Get topic's source IDs (simplified - would need item query)
            source_ids: list[int] = []

            contexts.append(
                TopicContext(
                    topic_id=topic.id,
                    title=topic.title,
                    summary=topic.summary,
                    tags=topic.metadata_json.get("tags", []) if topic.metadata_json else [],
                    last_seen_at=topic.last_seen_at,
                    source_ids=source_ids,
                    entities=[],  # TODO: Extract entities
                    item_count=topic.item_count,
                )
            )

        return contexts

    async def resolve_batch(
        self,
        items: list[NormalizedItemDTO],
        *,
        board_type: BoardType | None = None,
    ) -> list[MergeResult]:
        """Resolve merge decisions for multiple items.

        Args:
            items: List of items to process.
            board_type: Optional board type override.

        Returns:
            List of MergeResults.
        """
        results: list[MergeResult] = []

        for item in items:
            result = await self.resolve_for_item(item, board_type=board_type)
            results.append(result)

        return results
