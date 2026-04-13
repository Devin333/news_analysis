"""Tag service for unified tagging operations.

This module provides a unified interface for tagging items and topics,
combining rule-based tagging with future LLM-based enhancements.
"""

from dataclasses import dataclass, field

from app.bootstrap.logging import get_logger
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.tag import (
    ItemTagDTO,
    TagMatchDTO,
    TaggingResultDTO,
    TagType,
    TopicTagDTO,
)
from app.contracts.dto.topic import TopicReadDTO
from app.processing.tagging.rule_tagger import (
    RuleTagger,
    TaggerConfig,
    TaggingContext,
    get_rule_tagger,
)

logger = get_logger(__name__)


@dataclass
class TagServiceConfig:
    """Configuration for tag service."""

    # Whether to use rule-based tagging
    use_rule_tagger: bool = True

    # Whether to use LLM-based tagging (future)
    use_llm_tagger: bool = False

    # Minimum confidence to persist a tag
    min_persist_confidence: float = 0.5

    # Maximum tags per item
    max_tags_per_item: int = 20

    # Maximum tags per topic
    max_tags_per_topic: int = 30


@dataclass
class TagServiceResult:
    """Result of tag service operation."""

    item_id: int | None = None
    topic_id: int | None = None
    tags: list[TagMatchDTO] = field(default_factory=list)
    rule_tags: list[TagMatchDTO] = field(default_factory=list)
    llm_tags: list[TagMatchDTO] = field(default_factory=list)
    processing_time_ms: float = 0.0
    success: bool = True
    error: str | None = None


class TagService:
    """Unified service for tagging operations.

    Provides methods to tag items and topics using multiple
    tagging strategies (rule-based, LLM-based).
    """

    def __init__(
        self,
        config: TagServiceConfig | None = None,
        rule_tagger: RuleTagger | None = None,
    ) -> None:
        """Initialize the tag service.

        Args:
            config: Service configuration.
            rule_tagger: Optional custom rule tagger.
        """
        self._config = config or TagServiceConfig()
        self._rule_tagger = rule_tagger or get_rule_tagger()

    def tag_item(self, item: NormalizedItemDTO) -> TagServiceResult:
        """Tag a normalized item.

        Args:
            item: The normalized item to tag.

        Returns:
            TagServiceResult with matched tags.
        """
        import time

        start_time = time.perf_counter()

        all_tags: list[TagMatchDTO] = []
        rule_tags: list[TagMatchDTO] = []
        llm_tags: list[TagMatchDTO] = []

        try:
            # Rule-based tagging
            if self._config.use_rule_tagger:
                context = TaggingContext(
                    title=item.title,
                    excerpt=item.excerpt or "",
                    clean_text=item.clean_text or "",
                    source_type=None,
                    content_type=item.content_type.value if item.content_type else None,
                )
                rule_result = self._rule_tagger.tag(context)
                rule_tags = rule_result.matches

            # LLM-based tagging (future)
            if self._config.use_llm_tagger:
                # TODO: Implement LLM tagger
                pass

            # Merge and deduplicate tags
            all_tags = self._merge_tags(rule_tags, llm_tags)

            # Filter by confidence
            all_tags = [
                t for t in all_tags
                if t.confidence >= self._config.min_persist_confidence
            ]

            # Limit total tags
            all_tags = all_tags[: self._config.max_tags_per_item]

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                f"Tagged item '{item.title[:50]}...' with {len(all_tags)} tags "
                f"(rule={len(rule_tags)}, llm={len(llm_tags)}) in {elapsed_ms:.1f}ms"
            )

            return TagServiceResult(
                item_id=item.id,
                tags=all_tags,
                rule_tags=rule_tags,
                llm_tags=llm_tags,
                processing_time_ms=elapsed_ms,
                success=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Failed to tag item: {e}")
            return TagServiceResult(
                item_id=item.id,
                processing_time_ms=elapsed_ms,
                success=False,
                error=str(e),
            )

    def tag_topic(
        self,
        topic: TopicReadDTO,
        *,
        topic_text: str | None = None,
    ) -> TagServiceResult:
        """Tag a topic.

        Args:
            topic: The topic to tag.
            topic_text: Optional additional text for tagging.

        Returns:
            TagServiceResult with matched tags.
        """
        import time

        start_time = time.perf_counter()

        all_tags: list[TagMatchDTO] = []
        rule_tags: list[TagMatchDTO] = []
        llm_tags: list[TagMatchDTO] = []

        try:
            # Build tagging context from topic
            text_parts = [topic.title]
            if topic.summary:
                text_parts.append(topic.summary)
            if topic_text:
                text_parts.append(topic_text)

            # Rule-based tagging
            if self._config.use_rule_tagger:
                context = TaggingContext(
                    title=topic.title,
                    excerpt=topic.summary or "",
                    clean_text=" ".join(text_parts),
                )
                rule_result = self._rule_tagger.tag(context)
                rule_tags = rule_result.matches

            # LLM-based tagging (future)
            if self._config.use_llm_tagger:
                # TODO: Implement LLM tagger
                pass

            # Merge and deduplicate tags
            all_tags = self._merge_tags(rule_tags, llm_tags)

            # Filter by confidence
            all_tags = [
                t for t in all_tags
                if t.confidence >= self._config.min_persist_confidence
            ]

            # Limit total tags
            all_tags = all_tags[: self._config.max_tags_per_topic]

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                f"Tagged topic '{topic.title[:50]}...' with {len(all_tags)} tags "
                f"in {elapsed_ms:.1f}ms"
            )

            return TagServiceResult(
                topic_id=topic.id,
                tags=all_tags,
                rule_tags=rule_tags,
                llm_tags=llm_tags,
                processing_time_ms=elapsed_ms,
                success=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Failed to tag topic: {e}")
            return TagServiceResult(
                topic_id=topic.id,
                processing_time_ms=elapsed_ms,
                success=False,
                error=str(e),
            )

    def tag_text(self, text: str) -> TagServiceResult:
        """Tag plain text.

        Convenience method for tagging arbitrary text.

        Args:
            text: The text to tag.

        Returns:
            TagServiceResult with matched tags.
        """
        import time

        start_time = time.perf_counter()

        try:
            rule_result = self._rule_tagger.tag_text(text)
            all_tags = [
                t for t in rule_result.matches
                if t.confidence >= self._config.min_persist_confidence
            ]

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return TagServiceResult(
                tags=all_tags,
                rule_tags=rule_result.matches,
                processing_time_ms=elapsed_ms,
                success=True,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return TagServiceResult(
                processing_time_ms=elapsed_ms,
                success=False,
                error=str(e),
            )

    def _merge_tags(
        self,
        rule_tags: list[TagMatchDTO],
        llm_tags: list[TagMatchDTO],
    ) -> list[TagMatchDTO]:
        """Merge tags from different sources.

        Deduplicates by (tag_type, tag_name) and keeps highest confidence.

        Args:
            rule_tags: Tags from rule-based tagger.
            llm_tags: Tags from LLM tagger.

        Returns:
            Merged and deduplicated tag list.
        """
        # Use dict to deduplicate by (type, name)
        merged: dict[tuple[TagType, str], TagMatchDTO] = {}

        # Add rule tags first
        for tag in rule_tags:
            key = (tag.tag_type, tag.tag_name.lower())
            merged[key] = tag

        # Add LLM tags, keeping higher confidence
        for tag in llm_tags:
            key = (tag.tag_type, tag.tag_name.lower())
            existing = merged.get(key)
            if existing is None or tag.confidence > existing.confidence:
                merged[key] = tag

        # Sort by confidence descending
        result = list(merged.values())
        result.sort(key=lambda t: t.confidence, reverse=True)

        return result

    def to_item_tags(
        self,
        item_id: int,
        tags: list[TagMatchDTO],
    ) -> list[ItemTagDTO]:
        """Convert tag matches to item tag DTOs.

        Args:
            item_id: The item ID.
            tags: List of tag matches.

        Returns:
            List of ItemTagDTO.
        """
        return [
            ItemTagDTO(
                item_id=item_id,
                tag_id=tag.tag_id,
                tag_name=tag.tag_name,
                tag_type=tag.tag_type,
                confidence=tag.confidence,
                source=tag.match_source,
            )
            for tag in tags
        ]

    def to_topic_tags(
        self,
        topic_id: int,
        tags: list[TagMatchDTO],
    ) -> list[TopicTagDTO]:
        """Convert tag matches to topic tag DTOs.

        Args:
            topic_id: The topic ID.
            tags: List of tag matches.

        Returns:
            List of TopicTagDTO.
        """
        return [
            TopicTagDTO(
                topic_id=topic_id,
                tag_id=tag.tag_id,
                tag_name=tag.tag_name,
                tag_type=tag.tag_type,
                confidence=tag.confidence,
                item_count=1,
                source=tag.match_source,
            )
            for tag in tags
        ]

    def to_tagging_result_dto(self, result: TagServiceResult) -> TaggingResultDTO:
        """Convert service result to DTO.

        Args:
            result: The tag service result.

        Returns:
            TaggingResultDTO.
        """
        return TaggingResultDTO(
            item_id=result.item_id,
            topic_id=result.topic_id,
            tags=result.tags,
            processing_time_ms=result.processing_time_ms,
        )


# Singleton instance
_default_service: TagService | None = None


def get_tag_service() -> TagService:
    """Get the default tag service instance.

    Returns:
        The default TagService instance.
    """
    global _default_service
    if _default_service is None:
        _default_service = TagService()
    return _default_service
