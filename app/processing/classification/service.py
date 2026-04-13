"""Unified classification service.

This module provides a unified interface for content classification,
combining board classification and content type classification.
"""

from dataclasses import dataclass, field

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType, ContentType, SourceType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.processing.classification.board_classifier import (
    BoardClassificationResult,
    BoardClassifier,
    ClassificationConfidence,
    get_board_classifier,
)
from app.processing.classification.content_type_classifier import (
    ContentTypeClassifier,
    ContentTypeResult,
    get_content_type_classifier,
)

logger = get_logger(__name__)


@dataclass
class ClassificationResult:
    """Combined classification result."""

    # Board classification
    board_type: BoardType
    board_confidence: ClassificationConfidence
    board_confidence_score: float

    # Content type classification
    content_type: ContentType
    content_type_confidence: float

    # Optional fields with defaults
    secondary_board: BoardType | None = None
    rationale: str = ""
    processing_time_ms: float = 0.0


@dataclass
class ClassificationServiceConfig:
    """Configuration for classification service."""

    # Whether to use board classifier
    use_board_classifier: bool = True

    # Whether to use content type classifier
    use_content_type_classifier: bool = True

    # Default board type
    default_board: BoardType = BoardType.GENERAL

    # Default content type
    default_content_type: ContentType = ContentType.ARTICLE


class ClassificationService:
    """Unified service for content classification.

    Provides methods to classify items by board type and content type.
    """

    def __init__(
        self,
        config: ClassificationServiceConfig | None = None,
        board_classifier: BoardClassifier | None = None,
        content_type_classifier: ContentTypeClassifier | None = None,
    ) -> None:
        """Initialize the classification service.

        Args:
            config: Service configuration.
            board_classifier: Optional custom board classifier.
            content_type_classifier: Optional custom content type classifier.
        """
        self._config = config or ClassificationServiceConfig()
        self._board_classifier = board_classifier or get_board_classifier()
        self._content_type_classifier = content_type_classifier or get_content_type_classifier()

    def classify(self, item: NormalizedItemDTO) -> ClassificationResult:
        """Classify an item.

        Args:
            item: The normalized item to classify.

        Returns:
            ClassificationResult with board and content type.
        """
        import time

        start_time = time.perf_counter()

        # Board classification
        board_result: BoardClassificationResult | None = None
        if self._config.use_board_classifier:
            board_result = self._board_classifier.classify(item)

        # Content type classification
        content_type_result: ContentTypeResult | None = None
        if self._config.use_content_type_classifier:
            content_type_result = self._content_type_classifier.classify(
                title=item.title,
                url=item.canonical_url or "",
                source_type=None,
                content_length=len(item.clean_text) if item.clean_text else 0,
            )

        # Build combined result
        board_type = (
            board_result.primary_board
            if board_result
            else self._config.default_board
        )
        board_confidence = (
            board_result.confidence
            if board_result
            else ClassificationConfidence.LOW
        )
        board_confidence_score = (
            board_result.confidence_score
            if board_result
            else 0.3
        )
        secondary_board = board_result.secondary_board if board_result else None

        content_type = (
            content_type_result.content_type
            if content_type_result
            else self._config.default_content_type
        )
        content_type_confidence = (
            content_type_result.confidence
            if content_type_result
            else 0.3
        )

        # Build rationale
        rationale_parts = []
        if board_result:
            rationale_parts.append(f"board: {board_result.rationale}")
        if content_type_result:
            rationale_parts.append(f"type: {content_type_result.rationale}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        result = ClassificationResult(
            board_type=board_type,
            board_confidence=board_confidence,
            board_confidence_score=board_confidence_score,
            secondary_board=secondary_board,
            content_type=content_type,
            content_type_confidence=content_type_confidence,
            rationale="; ".join(rationale_parts),
            processing_time_ms=elapsed_ms,
        )

        logger.info(
            f"Classified '{item.title[:50]}...' as board={board_type.value}, "
            f"type={content_type.value} in {elapsed_ms:.1f}ms"
        )

        return result

    def classify_board(self, item: NormalizedItemDTO) -> BoardClassificationResult:
        """Classify only board type.

        Args:
            item: The normalized item.

        Returns:
            BoardClassificationResult.
        """
        return self._board_classifier.classify(item)

    def classify_content_type(
        self,
        *,
        title: str = "",
        url: str = "",
        source_type: SourceType | None = None,
        content_length: int = 0,
    ) -> ContentTypeResult:
        """Classify only content type.

        Args:
            title: Content title.
            url: Content URL.
            source_type: Type of source.
            content_length: Length of content.

        Returns:
            ContentTypeResult.
        """
        return self._content_type_classifier.classify(
            title=title,
            url=url,
            source_type=source_type,
            content_length=content_length,
        )

    def classify_batch(
        self,
        items: list[NormalizedItemDTO],
    ) -> list[ClassificationResult]:
        """Classify multiple items.

        Args:
            items: List of items to classify.

        Returns:
            List of classification results.
        """
        return [self.classify(item) for item in items]


# Singleton instance
_default_service: ClassificationService | None = None


def get_classification_service() -> ClassificationService:
    """Get the default classification service.

    Returns:
        The default ClassificationService instance.
    """
    global _default_service
    if _default_service is None:
        _default_service = ClassificationService()
    return _default_service
