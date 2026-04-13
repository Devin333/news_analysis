"""Board classifier for content categorization.

This module provides rule-based classification of content into
different boards (news, tech/AI, research, engineering).
"""

from dataclasses import dataclass
from enum import StrEnum

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType, ContentType, SourceType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.processing.classification.features import (
    ClassificationFeatures,
    extract_features,
)

logger = get_logger(__name__)


class ClassificationConfidence(StrEnum):
    """Confidence level for classification."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


@dataclass
class BoardClassificationResult:
    """Result of board classification."""

    primary_board: BoardType
    secondary_board: BoardType | None = None
    confidence: ClassificationConfidence = ClassificationConfidence.MEDIUM
    confidence_score: float = 0.5
    rationale: str = ""
    features: ClassificationFeatures | None = None


@dataclass
class ClassifierConfig:
    """Configuration for board classifier."""

    # Threshold for high confidence
    high_confidence_threshold: float = 0.7

    # Threshold for medium confidence
    medium_confidence_threshold: float = 0.4

    # Threshold for low confidence
    low_confidence_threshold: float = 0.2

    # Weight for source type in classification
    source_weight: float = 0.3

    # Weight for content type in classification
    content_type_weight: float = 0.2

    # Weight for title/keyword features
    keyword_weight: float = 0.3

    # Weight for tags
    tag_weight: float = 0.2


class BoardClassifier:
    """Rule-based board classifier.

    Classifies content into boards based on:
    - Source type (RSS, GitHub, arXiv, etc.)
    - Content type (article, paper, repository, etc.)
    - Title/content keywords
    - Tags
    """

    def __init__(self, config: ClassifierConfig | None = None) -> None:
        """Initialize the classifier.

        Args:
            config: Configuration for classification behavior.
        """
        self._config = config or ClassifierConfig()

    def classify(self, item: NormalizedItemDTO) -> BoardClassificationResult:
        """Classify an item into a board.

        Args:
            item: The normalized item to classify.

        Returns:
            BoardClassificationResult with classification details.
        """
        # Extract features
        features = extract_features(
            title=item.title,
            clean_text=item.clean_text or "",
            excerpt=item.excerpt or "",
            source_type=None,  # Would need source lookup
            content_type=item.content_type,
            tags=item.tags,
            source_trust_score=0.5,
        )

        # Compute board scores
        scores = self._compute_board_scores(features, item)

        # Determine primary and secondary boards
        sorted_boards = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_board = sorted_boards[0][0]
        primary_score = sorted_boards[0][1]

        secondary_board = None
        if len(sorted_boards) > 1 and sorted_boards[1][1] > 0.3:
            secondary_board = sorted_boards[1][0]

        # Determine confidence
        confidence, confidence_score = self._determine_confidence(
            primary_score,
            sorted_boards[1][1] if len(sorted_boards) > 1 else 0,
        )

        # Build rationale
        rationale = self._build_rationale(features, scores, primary_board)

        result = BoardClassificationResult(
            primary_board=primary_board,
            secondary_board=secondary_board,
            confidence=confidence,
            confidence_score=confidence_score,
            rationale=rationale,
            features=features,
        )

        logger.debug(
            f"Classified '{item.title[:50]}...' as {primary_board.value} "
            f"(confidence={confidence.value}, score={confidence_score:.2f})"
        )

        return result

    def _compute_board_scores(
        self,
        features: ClassificationFeatures,
        item: NormalizedItemDTO,
    ) -> dict[BoardType, float]:
        """Compute scores for each board type.

        Args:
            features: Extracted classification features.
            item: The normalized item.

        Returns:
            Dictionary mapping board type to score.
        """
        scores: dict[BoardType, float] = {
            BoardType.GENERAL: 0.1,  # Base score
            BoardType.AI: 0.0,
            BoardType.ENGINEERING: 0.0,
            BoardType.RESEARCH: 0.0,
        }

        # AI board scoring
        scores[BoardType.AI] = (
            features.ai_relevance * 0.5 +
            features.title_ai_score * 0.3 +
            (0.2 if features.content_type == ContentType.PAPER else 0) +
            (0.1 if features.source_type == SourceType.ARXIV else 0)
        )

        # Research board scoring
        scores[BoardType.RESEARCH] = (
            features.research_relevance * 0.5 +
            features.title_research_score * 0.3 +
            (0.3 if features.content_type == ContentType.PAPER else 0) +
            (0.2 if features.source_type == SourceType.ARXIV else 0)
        )

        # Engineering board scoring
        scores[BoardType.ENGINEERING] = (
            features.engineering_relevance * 0.5 +
            features.title_engineering_score * 0.3 +
            (0.3 if features.content_type == ContentType.REPOSITORY else 0) +
            (0.2 if features.source_type == SourceType.GITHUB else 0)
        )

        # General/News board scoring
        scores[BoardType.GENERAL] = max(
            0.1,
            features.news_relevance * 0.5 +
            features.title_news_score * 0.3 +
            (0.2 if features.content_type == ContentType.ARTICLE else 0)
        )

        # Apply existing board_type_candidate if present
        if item.board_type_candidate:
            scores[item.board_type_candidate] += 0.2

        # Normalize scores
        max_score = max(scores.values())
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _determine_confidence(
        self,
        primary_score: float,
        secondary_score: float,
    ) -> tuple[ClassificationConfidence, float]:
        """Determine confidence level.

        Args:
            primary_score: Score of primary board.
            secondary_score: Score of secondary board.

        Returns:
            Tuple of (confidence level, confidence score).
        """
        # Confidence based on score gap
        gap = primary_score - secondary_score

        if primary_score >= self._config.high_confidence_threshold and gap >= 0.3:
            return ClassificationConfidence.HIGH, primary_score

        if primary_score >= self._config.medium_confidence_threshold and gap >= 0.15:
            return ClassificationConfidence.MEDIUM, primary_score

        if primary_score >= self._config.low_confidence_threshold:
            return ClassificationConfidence.LOW, primary_score

        return ClassificationConfidence.UNCERTAIN, primary_score

    def _build_rationale(
        self,
        features: ClassificationFeatures,
        scores: dict[BoardType, float],
        primary_board: BoardType,
    ) -> str:
        """Build human-readable rationale.

        Args:
            features: Classification features.
            scores: Board scores.
            primary_board: Selected primary board.

        Returns:
            Rationale string.
        """
        reasons: list[str] = []

        if primary_board == BoardType.AI:
            if features.title_ai_score > 0.3:
                reasons.append("AI keywords in title")
            if features.content_type == ContentType.PAPER:
                reasons.append("paper content type")
            if features.source_type == SourceType.ARXIV:
                reasons.append("arXiv source")

        elif primary_board == BoardType.RESEARCH:
            if features.title_research_score > 0.3:
                reasons.append("research keywords in title")
            if features.content_type == ContentType.PAPER:
                reasons.append("paper content type")

        elif primary_board == BoardType.ENGINEERING:
            if features.title_engineering_score > 0.3:
                reasons.append("engineering keywords in title")
            if features.content_type == ContentType.REPOSITORY:
                reasons.append("repository content type")
            if features.source_type == SourceType.GITHUB:
                reasons.append("GitHub source")

        elif primary_board == BoardType.GENERAL:
            if features.title_news_score > 0.3:
                reasons.append("news keywords in title")
            if features.content_type == ContentType.ARTICLE:
                reasons.append("article content type")

        if not reasons:
            reasons.append("default classification")

        return "; ".join(reasons)

    def classify_batch(
        self,
        items: list[NormalizedItemDTO],
    ) -> list[BoardClassificationResult]:
        """Classify multiple items.

        Args:
            items: List of items to classify.

        Returns:
            List of classification results.
        """
        return [self.classify(item) for item in items]


# Singleton instance
_default_classifier: BoardClassifier | None = None


def get_board_classifier() -> BoardClassifier:
    """Get the default board classifier.

    Returns:
        The default BoardClassifier instance.
    """
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = BoardClassifier()
    return _default_classifier
