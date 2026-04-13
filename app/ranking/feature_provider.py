"""Ranking feature provider implementation.

Provides unified feature extraction for topics.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.dto.ranking import RankingContextDTO, RankingFeatureDTO
from app.contracts.protocols.ranking import RankingFeatureProviderProtocol
from app.ranking.features import (
    compute_analyst_importance_score,
    compute_board_weight,
    compute_historian_novelty_score,
    compute_homepage_candidate_score,
    compute_recency_score,
    compute_review_pass_bonus,
    compute_source_diversity_score,
    compute_stale_penalty,
    compute_topic_size_score,
    compute_trend_signal_score,
    compute_trusted_source_score,
)
from app.storage.repositories.review_repository import ReviewRepository
from app.storage.repositories.topic_insight_repository import TopicInsightRepository
from app.storage.repositories.topic_repository import TopicRepository


class RankingFeatureProvider(RankingFeatureProviderProtocol):
    """Provider for ranking features.

    Extracts features from various data sources for ranking.
    """

    def __init__(
        self,
        session: AsyncSession,
        topic_repo: TopicRepository | None = None,
        insight_repo: TopicInsightRepository | None = None,
        review_repo: ReviewRepository | None = None,
    ) -> None:
        """Initialize feature provider.

        Args:
            session: Database session
            topic_repo: Optional topic repository
            insight_repo: Optional insight repository
            review_repo: Optional review repository
        """
        self._session = session
        self._topic_repo = topic_repo or TopicRepository(session)
        self._insight_repo = insight_repo or TopicInsightRepository(session)
        self._review_repo = review_repo or ReviewRepository(session)

    async def get_features(
        self,
        topic_id: int,
        context: RankingContextDTO,
    ) -> RankingFeatureDTO:
        """Get ranking features for a single topic.

        Args:
            topic_id: The topic to get features for
            context: Ranking context

        Returns:
            RankingFeatureDTO with all computed features
        """
        now = datetime.now(timezone.utc)

        # Get topic data
        topic = await self._topic_repo.get_by_id(topic_id)
        if topic is None:
            return self._empty_features(topic_id, now)

        # Get insight data
        insight = await self._insight_repo.get_latest_by_topic_id(topic_id)

        # Get review data
        reviews = await self._review_repo.list_by_target("topic_copy", topic_id, limit=1)
        latest_review = reviews[0] if reviews else None

        # Compute features
        recency = compute_recency_score(
            topic.last_seen_at,
            context.time_window_hours,
            now,
        )

        stale = compute_stale_penalty(
            topic.last_seen_at,
            stale_threshold_hours=context.time_window_hours * 3,
            now=now,
        )

        source_diversity = compute_source_diversity_score(topic.source_count)

        # TODO: Get trusted source count from source metadata
        trusted_source = compute_trusted_source_score(
            trusted_source_count=topic.source_count // 2,  # Placeholder
            total_source_count=topic.source_count,
        )

        topic_size = compute_topic_size_score(topic.item_count)

        trend_signal = compute_trend_signal_score(
            float(topic.trend_score),
            signal_strength=insight.trend_momentum if insight else None,
            stage_label=insight.trend_stage if insight else None,
        )

        analyst_importance = 0.0
        if insight:
            analyst_importance = compute_analyst_importance_score(
                confidence=insight.confidence,
                trend_momentum=insight.trend_momentum,
                has_why_it_matters=bool(insight.why_it_matters),
                has_system_judgement=bool(insight.system_judgement),
            )

        # TODO: Get historian data
        historian_novelty = compute_historian_novelty_score(
            is_novel=None,
            historical_context_count=0,
            has_timeline=False,
        )

        review_passed = False
        review_bonus = 0.0
        if latest_review:
            review_passed = latest_review.review_status == "approve"
            review_bonus = compute_review_pass_bonus(
                latest_review.review_status,
                latest_review.confidence,
            )

        board_weight = compute_board_weight(
            topic.board_type.value,
            context.board_type,
        )

        homepage_candidate = compute_homepage_candidate_score(
            item_count=topic.item_count,
            source_count=topic.source_count,
            review_passed=review_passed,
            recency_score=recency,
            trend_score=float(topic.trend_score),
        )

        return RankingFeatureDTO(
            topic_id=topic_id,
            recency_score=recency,
            stale_penalty=stale,
            source_authority_score=trusted_source,
            source_diversity_score=source_diversity,
            trusted_source_score=trusted_source,
            topic_heat_score=float(topic.heat_score),
            topic_size_score=topic_size,
            item_count=topic.item_count,
            source_count=topic.source_count,
            trend_score=float(topic.trend_score),
            trend_signal_score=trend_signal,
            insight_confidence=insight.confidence if insight and insight.confidence else 0.0,
            analyst_importance_score=analyst_importance,
            historian_novelty_score=historian_novelty,
            review_passed=review_passed,
            review_pass_bonus=review_bonus,
            board_weight=board_weight,
            homepage_candidate_score=homepage_candidate,
            computed_at=now,
        )

    async def get_features_batch(
        self,
        topic_ids: list[int],
        context: RankingContextDTO,
    ) -> dict[int, RankingFeatureDTO]:
        """Get ranking features for multiple topics.

        Args:
            topic_ids: List of topic IDs
            context: Ranking context

        Returns:
            Dict mapping topic_id to RankingFeatureDTO
        """
        result = {}
        for topic_id in topic_ids:
            result[topic_id] = await self.get_features(topic_id, context)
        return result

    def _empty_features(
        self,
        topic_id: int,
        now: datetime,
    ) -> RankingFeatureDTO:
        """Create empty features for missing topic.

        Args:
            topic_id: Topic ID
            now: Current time

        Returns:
            RankingFeatureDTO with default values
        """
        return RankingFeatureDTO(
            topic_id=topic_id,
            computed_at=now,
        )


class CachedFeatureProvider(RankingFeatureProviderProtocol):
    """Feature provider with caching support.

    Wraps another provider and caches results.
    """

    def __init__(
        self,
        inner: RankingFeatureProviderProtocol,
        cache_ttl_seconds: int = 300,
    ) -> None:
        """Initialize cached provider.

        Args:
            inner: Inner feature provider
            cache_ttl_seconds: Cache TTL in seconds
        """
        self._inner = inner
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[datetime, RankingFeatureDTO]] = {}

    def _cache_key(self, topic_id: int, context: RankingContextDTO) -> str:
        """Generate cache key."""
        return f"{topic_id}:{context.context_name}:{context.time_window_hours}"

    def _is_valid(self, cached_at: datetime) -> bool:
        """Check if cache entry is still valid."""
        now = datetime.now(timezone.utc)
        age = (now - cached_at).total_seconds()
        return age < self._cache_ttl

    async def get_features(
        self,
        topic_id: int,
        context: RankingContextDTO,
    ) -> RankingFeatureDTO:
        """Get features with caching."""
        key = self._cache_key(topic_id, context)

        if key in self._cache:
            cached_at, features = self._cache[key]
            if self._is_valid(cached_at):
                return features

        features = await self._inner.get_features(topic_id, context)
        self._cache[key] = (datetime.now(timezone.utc), features)
        return features

    async def get_features_batch(
        self,
        topic_ids: list[int],
        context: RankingContextDTO,
    ) -> dict[int, RankingFeatureDTO]:
        """Get features batch with caching."""
        result = {}
        uncached_ids = []

        for topic_id in topic_ids:
            key = self._cache_key(topic_id, context)
            if key in self._cache:
                cached_at, features = self._cache[key]
                if self._is_valid(cached_at):
                    result[topic_id] = features
                    continue
            uncached_ids.append(topic_id)

        if uncached_ids:
            batch_result = await self._inner.get_features_batch(uncached_ids, context)
            now = datetime.now(timezone.utc)
            for topic_id, features in batch_result.items():
                key = self._cache_key(topic_id, context)
                self._cache[key] = (now, features)
                result[topic_id] = features

        return result

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def invalidate(self, topic_id: int) -> None:
        """Invalidate cache for a specific topic."""
        keys_to_remove = [k for k in self._cache if k.startswith(f"{topic_id}:")]
        for key in keys_to_remove:
            del self._cache[key]
