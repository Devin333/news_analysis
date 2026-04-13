"""Report Service for managing report generation.

Handles building daily and weekly reports with ranking-based selection.
"""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.ranking import RankingContextDTO
from app.contracts.dto.report import (
    ReportCreateDTO,
    ReportDTO,
    ReportSectionDTO,
    ReportTopicSummaryDTO,
)

if TYPE_CHECKING:
    from app.ranking.feature_provider import RankingFeatureProvider
    from app.ranking.service import RankingService
    from app.ranking.strategies.report_selection import ReportSelectionStrategy
    from app.storage.repositories.report_repository import ReportRepository
    from app.storage.repositories.topic_repository import TopicRepository
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class ReportService:
    """Service for report generation and management.

    Handles:
    - Selecting top topics for reports using ranking strategies
    - Building daily reports
    - Building weekly reports
    - Managing report lifecycle
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
            ranking_service: Optional ranking service for topic selection.
            feature_provider: Optional feature provider for ranking.
        """
        self._uow = uow
        self._ranking_service = ranking_service
        self._feature_provider = feature_provider

    async def build_daily_report(
        self,
        date: datetime | None = None,
        *,
        max_topics: int = 10,
        include_trends: bool = True,
    ) -> ReportDTO | None:
        """Build a daily report.

        Args:
            date: Report date (defaults to today).
            max_topics: Maximum topics to include.
            include_trends: Whether to include trend section.

        Returns:
            Generated ReportDTO or None.
        """
        if date is None:
            date = datetime.now(timezone.utc)

        logger.info(f"Building daily report for {date.date()}")

        # Select top topics
        topics = await self.select_top_topics_for_report(
            window_days=1,
            limit=max_topics,
        )

        if not topics:
            logger.warning("No topics found for daily report")
            return None

        # Build sections
        sections = await self._build_daily_sections(topics, include_trends)

        # Generate title and summary
        title = f"Daily Tech Intelligence Report - {date.strftime('%Y-%m-%d')}"
        executive_summary = await self._generate_executive_summary(topics, "daily")

        # Create report
        create_dto = ReportCreateDTO(
            report_type="daily",
            report_date=date,
            title=title,
            executive_summary=executive_summary,
            sections=sections,
            topic_ids=[t["id"] for t in topics],
            metadata={
                "generated_by": "report_service",
                "topic_count": len(topics),
            },
        )

        # Save to database
        if self._uow and hasattr(self._uow, "reports"):
            report = await self._uow.reports.create(create_dto)
            return await self._uow.reports.get_by_id(report.id)

        # Return without persistence
        return ReportDTO(
            report_type=create_dto.report_type,
            report_date=create_dto.report_date,
            title=create_dto.title,
            executive_summary=create_dto.executive_summary,
            sections=create_dto.sections,
            topic_count=len(topics),
            generated_at=datetime.now(timezone.utc),
            status="draft",
        )

    async def build_weekly_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        *,
        max_topics: int = 20,
    ) -> ReportDTO | None:
        """Build a weekly report.

        Args:
            start_date: Week start date.
            end_date: Week end date.
            max_topics: Maximum topics to include.

        Returns:
            Generated ReportDTO or None.
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        logger.info(f"Building weekly report for {start_date.date()} to {end_date.date()}")

        # Select top topics for the week
        topics = await self.select_top_topics_for_report(
            window_days=7,
            limit=max_topics,
        )

        if not topics:
            logger.warning("No topics found for weekly report")
            return None

        # Build sections
        sections = await self._build_weekly_sections(topics)

        # Generate title and summary
        week_key = start_date.strftime("%Y-W%W")
        title = f"Weekly Tech Intelligence Report - {week_key}"
        executive_summary = await self._generate_executive_summary(topics, "weekly")

        # Create report
        create_dto = ReportCreateDTO(
            report_type="weekly",
            report_date=start_date,
            title=title,
            executive_summary=executive_summary,
            sections=sections,
            topic_ids=[t["id"] for t in topics],
            metadata={
                "generated_by": "report_service",
                "week_key": week_key,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "topic_count": len(topics),
            },
        )

        # Save to database
        if self._uow and hasattr(self._uow, "reports"):
            report = await self._uow.reports.create(create_dto)
            return await self._uow.reports.get_by_id(report.id)

        return ReportDTO(
            report_type=create_dto.report_type,
            report_date=create_dto.report_date,
            title=create_dto.title,
            executive_summary=create_dto.executive_summary,
            sections=create_dto.sections,
            topic_count=len(topics),
            generated_at=datetime.now(timezone.utc),
            status="draft",
        )

    async def select_top_topics_for_report(
        self,
        *,
        window_days: int = 1,
        limit: int = 10,
        use_ranking: bool = True,
    ) -> list[dict[str, Any]]:
        """Select top topics for a report.

        Uses ranking service if available, otherwise falls back to simple scoring.

        Selection criteria:
        - Recent activity (within window)
        - High heat score
        - High trend score
        - Source diversity
        - Has insights/analysis
        - Review status (via ranking)

        Args:
            window_days: Days to look back.
            limit: Maximum topics.
            use_ranking: Whether to use ranking service.

        Returns:
            List of topic dicts with scores.
        """
        if self._uow is None or not hasattr(self._uow, "topics"):
            return []

        # Get recent topics
        topics = await self._uow.topics.list_recent(limit=limit * 3)

        # Try ranking service first
        if use_ranking and self._ranking_service and self._feature_provider:
            return await self._select_with_ranking(topics, window_days, limit)

        # Fallback to simple scoring
        scored_topics = []
        for topic in topics:
            score = self._calculate_report_score(topic, window_days)
            scored_topics.append({
                "id": topic.id,
                "title": topic.title,
                "summary": topic.summary,
                "board_type": str(topic.board_type),
                "heat_score": float(topic.heat_score),
                "trend_score": float(topic.trend_score),
                "item_count": topic.item_count,
                "source_count": topic.source_count,
                "report_score": score,
            })

        # Sort by report score
        scored_topics.sort(key=lambda x: x["report_score"], reverse=True)

        return scored_topics[:limit]

    async def _select_with_ranking(
        self,
        topics: list[Any],
        window_days: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Select topics using ranking service.

        Args:
            topics: List of topic DTOs.
            window_days: Time window in days.
            limit: Maximum topics.

        Returns:
            List of topic dicts with ranking scores.
        """
        if not self._ranking_service or not self._feature_provider:
            return []

        # Build context
        context = RankingContextDTO(
            context_name="daily_report" if window_days <= 1 else "weekly_report",
            time_window_hours=window_days * 24,
            max_results=limit,
            include_unreviewed=False,
            min_item_count=1,
            min_source_count=1,
        )

        # Get topic IDs
        topic_ids = [t.id for t in topics]

        # Get features
        features_map = await self._feature_provider.get_features_batch(topic_ids, context)

        # Build topic_features list
        topic_features = [
            (t.id, features_map[t.id])
            for t in topics
            if t.id in features_map
        ]

        # Rank topics
        ranked = self._ranking_service.get_strategy(context.context_name)
        if ranked is None:
            # Fallback if no strategy registered
            return []

        ranked_topics = ranked.rank_topics(topic_features, context)

        # Convert to dict format
        topic_map = {t.id: t for t in topics}
        result = []
        for rt in ranked_topics[:limit]:
            topic = topic_map.get(rt.topic_id)
            if topic:
                result.append({
                    "id": topic.id,
                    "title": topic.title,
                    "summary": topic.summary,
                    "board_type": str(topic.board_type),
                    "heat_score": float(topic.heat_score),
                    "trend_score": float(topic.trend_score),
                    "item_count": topic.item_count,
                    "source_count": topic.source_count,
                    "report_score": rt.score,
                    "ranking_features": rt.features.model_dump() if rt.features else None,
                })

        return result

    def _calculate_report_score(
        self,
        topic: Any,
        window_days: int,
    ) -> float:
        """Calculate report inclusion score for a topic."""
        score = 0.0

        # Heat score component (40%)
        score += float(topic.heat_score) / 100 * 0.4

        # Trend score component (30%)
        score += float(topic.trend_score) * 0.3

        # Item count component (15%)
        item_score = min(1.0, topic.item_count / 20)
        score += item_score * 0.15

        # Source diversity component (15%)
        source_score = min(1.0, topic.source_count / 5)
        score += source_score * 0.15

        return score

    async def _build_daily_sections(
        self,
        topics: list[dict[str, Any]],
        include_trends: bool,
    ) -> list[ReportSectionDTO]:
        """Build sections for daily report."""
        sections = []

        # Top Stories section
        top_topics = topics[:5]
        if top_topics:
            sections.append(ReportSectionDTO(
                section_id="top_stories",
                section_title="Today's Top Stories",
                section_intro="The most significant developments in tech today.",
                key_points=[t["title"] for t in top_topics[:3]],
                topic_summaries=[
                    ReportTopicSummaryDTO(
                        topic_id=t["id"],
                        title=t["title"],
                        summary=t.get("summary") or "",
                        heat_score=t["heat_score"],
                    )
                    for t in top_topics
                ],
            ))

        # Trending section
        if include_trends:
            trending = [t for t in topics if t["trend_score"] > 0.5][:5]
            if trending:
                sections.append(ReportSectionDTO(
                    section_id="trending",
                    section_title="Trending Topics",
                    section_intro="Topics gaining momentum today.",
                    key_points=[t["title"] for t in trending[:3]],
                    topic_summaries=[
                        ReportTopicSummaryDTO(
                            topic_id=t["id"],
                            title=t["title"],
                            summary=t.get("summary") or "",
                            trend_stage="rising",
                            heat_score=t["heat_score"],
                        )
                        for t in trending
                    ],
                ))

        # Other notable section
        other = topics[5:10]
        if other:
            sections.append(ReportSectionDTO(
                section_id="notable",
                section_title="Other Notable Developments",
                section_intro="Additional stories worth watching.",
                topic_summaries=[
                    ReportTopicSummaryDTO(
                        topic_id=t["id"],
                        title=t["title"],
                        summary=t.get("summary") or "",
                        heat_score=t["heat_score"],
                    )
                    for t in other
                ],
            ))

        return sections

    async def _build_weekly_sections(
        self,
        topics: list[dict[str, Any]],
    ) -> list[ReportSectionDTO]:
        """Build sections for weekly report."""
        sections = []

        # Week's highlights
        highlights = topics[:7]
        if highlights:
            sections.append(ReportSectionDTO(
                section_id="highlights",
                section_title="This Week's Highlights",
                section_intro="The most important developments this week.",
                key_points=[t["title"] for t in highlights[:5]],
                topic_summaries=[
                    ReportTopicSummaryDTO(
                        topic_id=t["id"],
                        title=t["title"],
                        summary=t.get("summary") or "",
                        heat_score=t["heat_score"],
                    )
                    for t in highlights
                ],
            ))

        # Emerging trends
        emerging = [t for t in topics if t["trend_score"] > 0.6][:5]
        if emerging:
            sections.append(ReportSectionDTO(
                section_id="emerging_trends",
                section_title="Emerging Trends",
                section_intro="Topics showing strong momentum this week.",
                key_points=[t["title"] for t in emerging[:3]],
                topic_summaries=[
                    ReportTopicSummaryDTO(
                        topic_id=t["id"],
                        title=t["title"],
                        summary=t.get("summary") or "",
                        trend_stage="emerging",
                        heat_score=t["heat_score"],
                    )
                    for t in emerging
                ],
            ))

        # By category (group by board_type)
        by_board: dict[str, list[dict]] = {}
        for t in topics:
            board = t.get("board_type", "general")
            if board not in by_board:
                by_board[board] = []
            by_board[board].append(t)

        for board, board_topics in by_board.items():
            if len(board_topics) >= 2:
                sections.append(ReportSectionDTO(
                    section_id=f"category_{board}",
                    section_title=f"{board.replace('_', ' ').title()} Updates",
                    section_intro=f"Key developments in {board.replace('_', ' ')}.",
                    topic_summaries=[
                        ReportTopicSummaryDTO(
                            topic_id=t["id"],
                            title=t["title"],
                            summary=t.get("summary") or "",
                            heat_score=t["heat_score"],
                        )
                        for t in board_topics[:5]
                    ],
                ))

        return sections

    async def _generate_executive_summary(
        self,
        topics: list[dict[str, Any]],
        report_type: str,
    ) -> str:
        """Generate executive summary for report.

        This is a placeholder - in production, this would use
        the ReportEditorAgent to generate a proper summary.
        """
        if not topics:
            return "No significant developments to report."

        top_titles = [t["title"] for t in topics[:3]]

        if report_type == "daily":
            return (
                f"Today's report covers {len(topics)} key developments in tech. "
                f"Top stories include: {', '.join(top_titles)}."
            )
        else:
            return (
                f"This week's report highlights {len(topics)} significant topics. "
                f"Key developments include: {', '.join(top_titles)}."
            )

    async def get_daily_report(self, date: datetime) -> ReportDTO | None:
        """Get daily report by date."""
        if self._uow and hasattr(self._uow, "reports"):
            return await self._uow.reports.get_daily_by_date(date)
        return None

    async def get_weekly_report(self, week_key: str) -> ReportDTO | None:
        """Get weekly report by week key."""
        if self._uow and hasattr(self._uow, "reports"):
            return await self._uow.reports.get_weekly_by_key(week_key)
        return None

    async def list_recent_reports(
        self,
        *,
        report_type: str | None = None,
        limit: int = 20,
    ) -> list[ReportDTO]:
        """List recent reports."""
        if self._uow and hasattr(self._uow, "reports"):
            return await self._uow.reports.list_recent(
                report_type=report_type,
                limit=limit,
            )
        return []

    async def publish_report(self, report_id: int) -> bool:
        """Publish a report."""
        if self._uow and hasattr(self._uow, "reports"):
            result = await self._uow.reports.update_status(report_id, "published")
            return result is not None
        return False
