"""Enrichment pipeline for normalized items.

This module provides a pipeline to enrich normalized items with:
- Content type classification
- Board classification
- Rule-based tagging
"""

from dataclasses import dataclass, field
from typing import Any

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType, ContentType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.tag import TagMatchDTO
from app.processing.classification.service import (
    ClassificationResult,
    ClassificationService,
    get_classification_service,
)
from app.processing.tagging.tag_service import (
    TagService,
    TagServiceResult,
    get_tag_service,
)

logger = get_logger(__name__)


@dataclass
class EnrichmentResult:
    """Result of enrichment pipeline."""

    # Original item
    item_id: int | None = None

    # Classification results
    board_type: BoardType = BoardType.GENERAL
    content_type: ContentType = ContentType.ARTICLE
    board_confidence: float = 0.0
    content_type_confidence: float = 0.0

    # Tagging results
    tags: list[TagMatchDTO] = field(default_factory=list)

    # Processing info
    classification_time_ms: float = 0.0
    tagging_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # Success flag
    success: bool = True
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "board_type": self.board_type.value,
            "content_type": self.content_type.value,
            "board_confidence": self.board_confidence,
            "content_type_confidence": self.content_type_confidence,
            "tag_count": len(self.tags),
            "tags": [t.tag_name for t in self.tags],
            "total_time_ms": self.total_time_ms,
            "success": self.success,
        }


@dataclass
class EnrichmentConfig:
    """Configuration for enrichment pipeline."""

    # Whether to run classification
    enable_classification: bool = True

    # Whether to run tagging
    enable_tagging: bool = True

    # Whether to update item with results
    update_item: bool = True

    # Minimum confidence to apply classification
    min_classification_confidence: float = 0.3

    # Minimum confidence to apply tags
    min_tag_confidence: float = 0.5


class EnrichmentPipeline:
    """Pipeline for enriching normalized items.

    Runs classification and tagging on items to add:
    - board_type_candidate
    - content_type
    - tags
    """

    def __init__(
        self,
        config: EnrichmentConfig | None = None,
        classification_service: ClassificationService | None = None,
        tag_service: TagService | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            config: Pipeline configuration.
            classification_service: Optional custom classification service.
            tag_service: Optional custom tag service.
        """
        self._config = config or EnrichmentConfig()
        self._classification_service = classification_service or get_classification_service()
        self._tag_service = tag_service or get_tag_service()

    def enrich(self, item: NormalizedItemDTO) -> EnrichmentResult:
        """Enrich a normalized item.

        Args:
            item: The item to enrich.

        Returns:
            EnrichmentResult with enrichment details.
        """
        import time

        start_time = time.perf_counter()

        result = EnrichmentResult(item_id=item.id)
        errors: list[str] = []

        # Classification
        classification_result: ClassificationResult | None = None
        if self._config.enable_classification:
            try:
                classification_result = self._classification_service.classify(item)
                result.board_type = classification_result.board_type
                result.content_type = classification_result.content_type
                result.board_confidence = classification_result.board_confidence_score
                result.content_type_confidence = classification_result.content_type_confidence
                result.classification_time_ms = classification_result.processing_time_ms
            except Exception as e:
                errors.append(f"Classification failed: {e}")
                logger.error(f"Classification failed for item {item.id}: {e}")

        # Tagging
        tag_result: TagServiceResult | None = None
        if self._config.enable_tagging:
            try:
                tag_result = self._tag_service.tag_item(item)
                if tag_result.success:
                    result.tags = tag_result.tags
                    result.tagging_time_ms = tag_result.processing_time_ms
                else:
                    errors.append(f"Tagging failed: {tag_result.error}")
            except Exception as e:
                errors.append(f"Tagging failed: {e}")
                logger.error(f"Tagging failed for item {item.id}: {e}")

        # Update item if configured
        if self._config.update_item:
            self._apply_to_item(item, result)

        result.total_time_ms = (time.perf_counter() - start_time) * 1000
        result.errors = errors
        result.success = len(errors) == 0

        logger.info(
            f"Enriched item '{item.title[:50]}...' "
            f"(board={result.board_type.value}, type={result.content_type.value}, "
            f"tags={len(result.tags)}) in {result.total_time_ms:.1f}ms"
        )

        return result

    def _apply_to_item(
        self,
        item: NormalizedItemDTO,
        result: EnrichmentResult,
    ) -> None:
        """Apply enrichment results to item.

        Args:
            item: The item to update.
            result: The enrichment result.
        """
        # Apply board type if confidence is sufficient
        if result.board_confidence >= self._config.min_classification_confidence:
            item.board_type_candidate = result.board_type

        # Apply content type if confidence is sufficient
        if result.content_type_confidence >= self._config.min_classification_confidence:
            item.content_type = result.content_type

        # Apply tags
        if result.tags:
            item.tags = [
                t.tag_name for t in result.tags
                if t.confidence >= self._config.min_tag_confidence
            ]

    def enrich_batch(
        self,
        items: list[NormalizedItemDTO],
    ) -> list[EnrichmentResult]:
        """Enrich multiple items.

        Args:
            items: List of items to enrich.

        Returns:
            List of enrichment results.
        """
        results: list[EnrichmentResult] = []

        for item in items:
            result = self.enrich(item)
            results.append(result)

        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Enriched {len(items)} items: {success_count} successful, "
            f"{len(items) - success_count} failed"
        )

        return results


# Singleton instance
_default_pipeline: EnrichmentPipeline | None = None


def get_enrichment_pipeline() -> EnrichmentPipeline:
    """Get the default enrichment pipeline.

    Returns:
        The default EnrichmentPipeline instance.
    """
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = EnrichmentPipeline()
    return _default_pipeline
