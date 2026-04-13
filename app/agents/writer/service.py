"""Writer Agent service.

Provides high-level methods for generating different types of content copy.
"""

from typing import TYPE_CHECKING, Any

from app.agents.writer.agent import WriterAgent, create_writer_agent
from app.agents.writer.input_builder import WriterInputBuilder
from app.agents.writer.schemas import (
    CopyType,
    FeedCardCopyDTO,
    ReportSectionCopyDTO,
    TopicIntroCopyDTO,
    TrendCardCopyDTO,
    WriterOutput,
)
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.topic import TopicReadDTO
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class WriterService:
    """Service for generating content copy.

    Provides methods for generating different types of copy
    for topics.
    """

    def __init__(
        self,
        uow: "UnitOfWork | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            uow: Unit of work for database access.
        """
        self._uow = uow
        self._input_builder = WriterInputBuilder()
        self._agents: dict[CopyType, WriterAgent] = {}

    def _get_agent(self, copy_type: CopyType) -> WriterAgent:
        """Get or create an agent for a copy type.

        Args:
            copy_type: Type of copy.

        Returns:
            WriterAgent for the copy type.
        """
        if copy_type not in self._agents:
            self._agents[copy_type] = create_writer_agent(copy_type)
        return self._agents[copy_type]

    async def write_feed_card(
        self,
        topic_id: int,
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[FeedCardCopyDTO | None, dict[str, Any]]:
        """Generate feed card copy for a topic.

        Args:
            topic_id: ID of the topic.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (FeedCardCopyDTO or None, metadata).
        """
        topic = await self._get_topic(topic_id)
        if topic is None:
            return None, {"error": "Topic not found"}

        tags = await self._get_topic_tags(topic_id)
        representative_items = await self._get_representative_items(topic_id)

        writer_input = self._input_builder.build_feed_card_input(
            topic=topic,
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
            tags=tags,
        )

        agent = self._get_agent(CopyType.FEED_CARD)
        output, meta = await agent.write(writer_input)

        if output and output.feed_card:
            return output.feed_card, meta or {}

        return None, meta or {}

    async def write_topic_intro(
        self,
        topic_id: int,
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[TopicIntroCopyDTO | None, dict[str, Any]]:
        """Generate topic intro copy for a topic.

        Args:
            topic_id: ID of the topic.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (TopicIntroCopyDTO or None, metadata).
        """
        topic = await self._get_topic(topic_id)
        if topic is None:
            return None, {"error": "Topic not found"}

        tags = await self._get_topic_tags(topic_id)
        representative_items = await self._get_representative_items(topic_id)
        timeline_points = await self._get_timeline_points(topic_id)

        writer_input = self._input_builder.build_topic_intro_input(
            topic=topic,
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
            tags=tags,
            timeline_points=timeline_points,
        )

        agent = self._get_agent(CopyType.TOPIC_INTRO)
        output, meta = await agent.write(writer_input)

        if output and output.topic_intro:
            return output.topic_intro, meta or {}

        return None, meta or {}

    async def write_trend_card(
        self,
        topic_id: int,
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        trend_signals: list[dict[str, Any]] | None = None,
    ) -> tuple[TrendCardCopyDTO | None, dict[str, Any]]:
        """Generate trend card copy for a topic.

        Args:
            topic_id: ID of the topic.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.
            trend_signals: Optional trend signals.

        Returns:
            Tuple of (TrendCardCopyDTO or None, metadata).
        """
        topic = await self._get_topic(topic_id)
        if topic is None:
            return None, {"error": "Topic not found"}

        tags = await self._get_topic_tags(topic_id)
        representative_items = await self._get_representative_items(topic_id)

        writer_input = self._input_builder.build_trend_card_input(
            topic=topic,
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
            tags=tags,
            trend_signals=trend_signals,
        )

        agent = self._get_agent(CopyType.TREND_CARD)
        output, meta = await agent.write(writer_input)

        if output and output.trend_card:
            return output.trend_card, meta or {}

        return None, meta or {}

    async def write_report_section(
        self,
        topic_ids: list[int],
        *,
        section_theme: str = "General",
        report_type: str = "daily",
        topic_enrichments: dict[int, dict[str, Any]] | None = None,
    ) -> tuple[ReportSectionCopyDTO | None, dict[str, Any]]:
        """Generate report section copy for multiple topics.

        Args:
            topic_ids: IDs of topics in this section.
            section_theme: Theme of the section.
            report_type: Type of report (daily/weekly).
            topic_enrichments: Dict of topic_id -> enrichment data.

        Returns:
            Tuple of (ReportSectionCopyDTO or None, metadata).
        """
        topics = []
        for topic_id in topic_ids:
            topic = await self._get_topic(topic_id)
            if topic:
                topics.append(topic)

        if not topics:
            return None, {"error": "No topics found"}

        writer_input = self._input_builder.build_report_section_input(
            topics=topics,
            section_theme=section_theme,
            report_type=report_type,
            topic_enrichments=topic_enrichments,
        )

        agent = self._get_agent(CopyType.REPORT_SECTION)
        output, meta = await agent.write(writer_input)

        if output and output.report_section:
            return output.report_section, meta or {}

        return None, meta or {}

    async def _get_topic(self, topic_id: int) -> "TopicReadDTO | None":
        """Get topic by ID.

        Args:
            topic_id: Topic ID.

        Returns:
            TopicReadDTO or None.
        """
        if self._uow is None or self._uow.topics is None:
            logger.warning("UoW or topics repository not available")
            return None

        return await self._uow.topics.get_by_id(topic_id)

    async def _get_topic_tags(self, topic_id: int) -> list[str]:
        """Get tags for a topic.

        Args:
            topic_id: Topic ID.

        Returns:
            List of tag names.
        """
        # Stub - would query tag repository
        return []

    async def _get_representative_items(
        self,
        topic_id: int,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Get representative items for a topic.

        Args:
            topic_id: Topic ID.
            limit: Maximum items.

        Returns:
            List of item dicts.
        """
        # Stub - would query items
        return []

    async def _get_timeline_points(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get timeline points for a topic.

        Args:
            topic_id: Topic ID.
            limit: Maximum points.

        Returns:
            List of timeline point dicts.
        """
        # Stub - would query timeline
        return []
