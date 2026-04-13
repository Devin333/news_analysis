"""Feed Service for building ranked feeds.

Provides unified feed building with ranking and pagination.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.ranking import RankedTopicDTO, RankingContextDTO

if TYPE_CHECKING:
    from app.ranking.feature_provider import RankingFeatureProvider
    from app.ranking.service import RankingService
    from app.storage.repositories.topic_repository import TopicRepository
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class FeedService:
    """Service for building ranked feeds.

    Handles:
    - News feed ranking
    - Tech feed ranking
    - Homepage feed
    - Pagination
    """

    def __init__(
        self,
        uow: "UnitOfWork | None" = None,
        ranking_service: "RankingService | None" = None,
        feature_provider: "RankingFeatureProvider | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            uow: Unit of work for database access.
            ranking_service: Ranking service for scoring.
            feature_provider: Feature provider for ranking.
        """
        self._uow = uow
        self._ranking_service = ranking_service
        self._feature_provider = feature_provider

    async def get_news_feed(
        self,
        *,
        board_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
        time_window_hours: int = 48,
        include_unreviewed: bool = False,
    ) -> dict[str, Any]:
        """Get ranked news feed.

        Args:
            board_type: Optional board type filter.
            page: Page number (1-indexed).
            page_size: Items per page.
            time_window_hours: Time window for recency.
            include_unreviewed: Whether to include unreviewed topics.

        Returns:
            Dict with items, pagination info, and metadata.
        """
        context_name = f"{board_type}_news" if board_type else "news_feed"
        context = RankingContextDTO(
            context_name=context_name,
            board_type=board_type,
            time_window_hours=time_window_hours,
            max_results=page_size * 3,  # Get more for pagination
            include_unreviewed=include_unreviewed,
        )

        ranked = await self._get_ranked_topics(context)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        page_items = ranked[start:end]

        return {
            "items": [self._to_feed_item(t) for t in page_items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": len(ranked),
                "total_pages": (len(ranked) + page_size - 1) // page_size,
                "has_next": end < len(ranked),
                "has_prev": page > 1,
            },
            "metadata": {
                "context": context_name,
                "time_window_hours": time_window_hours,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def get_tech_feed(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        time_window_hours: int = 72,
        include_unreviewed: bool = True,
    ) -> dict[str, Any]:
        """Get ranked tech feed.

        Args:
            page: Page number.
            page_size: Items per page.
            time_window_hours: Time window.
            include_unreviewed: Include unreviewed topics.

        Returns:
            Dict with items and pagination.
        """
        context = RankingContextDTO(
            context_name="tech_feed",
            time_window_hours=time_window_hours,
            max_results=page_size * 3,
            include_unreviewed=include_unreviewed,
        )

        ranked = await self._get_ranked_topics(context)

        start = (page - 1) * page_size
        end = start + page_size
        page_items = ranked[start:end]

        return {
            "items": [self._to_feed_item(t) for t in page_items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": len(ranked),
                "total_pages": (len(ranked) + page_size - 1) // page_size,
                "has_next": end < len(ranked),
                "has_prev": page > 1,
            },
            "metadata": {
                "context": "tech_feed",
                "time_window_hours": time_window_hours,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def get_homepage_feed(
        self,
        *,
        max_items: int = 20,
    ) -> dict[str, Any]:
        """Get homepage feed with board balancing.

        Args:
            max_items: Maximum items to return.

        Returns:
            Dict with items and metadata.
        """
        context = RankingContextDTO(
            context_name="homepage",
            time_window_hours=48,
            max_results=max_items,
            include_unreviewed=False,
            min_item_count=2,
            min_source_count=2,
        )

        ranked = await self._get_ranked_topics(context)

        return {
            "items": [self._to_feed_item(t) for t in ranked[:max_items]],
            "metadata": {
                "context": "homepage",
                "item_count": len(ranked[:max_items]),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def get_board_feed(
        self,
        board_type: str,
        *,
        page: int = 1,
        page_size: int = 20,
        time_window_hours: int = 72,
    ) -> dict[str, Any]:
        """Get feed for a specific board.

        Args:
            board_type: Board type (ai, engineering, research, general).
            page: Page number.
            page_size: Items per page.
            time_window_hours: Time window.

        Returns:
            Dict with items and pagination.
        """
        context = RankingContextDTO(
            context_name=f"{board_type}_feed",
            board_type=board_type,
            time_window_hours=time_window_hours,
            max_results=page_size * 3,
            include_unreviewed=False,
        )

        ranked = await self._get_ranked_topics(context)

        start = (page - 1) * page_size
        end = start + page_size
        page_items = ranked[start:end]

        return {
            "items": [self._to_feed_item(t) for t in page_items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": len(ranked),
                "total_pages": (len(ranked) + page_size - 1) // page_size,
                "has_next": end < len(ranked),
                "has_prev": page > 1,
            },
            "metadata": {
                "context": f"{board_type}_feed",
                "board_type": board_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def _get_ranked_topics(
        self,
        context: RankingContextDTO,
    ) -> list[RankedTopicDTO]:
        """Get ranked topics for a context.

        Args:
            context: Ranking context.

        Returns:
            List of ranked topics.
        """
        if self._uow is None or not hasattr(self._uow, "topics"):
            return []

        # Get candidate topics
        if context.board_type:
            from app.common.enums import BoardType
            topics = await self._uow.topics.list_by_board(
                BoardType(context.board_type),
                limit=context.max_results * 2,
            )
        else:
            topics = await self._uow.topics.list_recent(limit=context.max_results * 2)

        if not topics:
            return []

        # Use ranking service if available
        if self._ranking_service and self._feature_provider:
            topic_ids = [t.id for t in topics]
            features_map = await self._feature_provider.get_features_batch(
                topic_ids, context
            )

            topic_features = [
                (t.id, features_map[t.id])
                for t in topics
                if t.id in features_map
            ]

            ranked = await self._ranking_service.rank_topics(topic_features, context)

            # Fill in topic details
            topic_map = {t.id: t for t in topics}
            for rt in ranked:
                topic = topic_map.get(rt.topic_id)
                if topic:
                    rt.title = topic.title
                    rt.board_type = str(topic.board_type)
                    rt.summary = topic.summary
                    rt.first_seen_at = topic.first_seen_at
                    rt.last_seen_at = topic.last_seen_at
                    rt.item_count = topic.item_count

            return ranked

        # Fallback: simple ranking by heat_score
        return [
            RankedTopicDTO(
                topic_id=t.id,
                rank=i + 1,
                score=float(t.heat_score),
                title=t.title,
                board_type=str(t.board_type),
                summary=t.summary,
                first_seen_at=t.first_seen_at,
                last_seen_at=t.last_seen_at,
                item_count=t.item_count,
            )
            for i, t in enumerate(
                sorted(topics, key=lambda x: float(x.heat_score), reverse=True)
            )
        ]

    def _to_feed_item(self, ranked: RankedTopicDTO) -> dict[str, Any]:
        """Convert ranked topic to feed item.

        Args:
            ranked: Ranked topic DTO.

        Returns:
            Feed item dict.
        """
        return {
            "topic_id": ranked.topic_id,
            "rank": ranked.rank,
            "score": ranked.score,
            "title": ranked.title,
            "summary": ranked.summary,
            "board_type": ranked.board_type,
            "item_count": ranked.item_count,
            "first_seen_at": (
                ranked.first_seen_at.isoformat() if ranked.first_seen_at else None
            ),
            "last_seen_at": (
                ranked.last_seen_at.isoformat() if ranked.last_seen_at else None
            ),
            "strategy": ranked.strategy_name,
        }
