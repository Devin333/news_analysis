"""Normalizer for converting parsed content to NormalizedItemDTO."""

from datetime import datetime, timezone
from typing import Any

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType, ContentType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.processing.cleaner import clean_text, clean_title

logger = get_logger(__name__)


class ContentNormalizer:
    """Normalize parsed content into NormalizedItemDTO.

    Responsibilities:
    - Apply text cleaning
    - Infer content type
    - Infer board type
    - Calculate quality score
    - Generate canonical URL
    """

    # Minimum quality thresholds
    MIN_WORD_COUNT = 50
    MIN_TITLE_LENGTH = 10

    # Board type keywords
    BOARD_KEYWORDS: dict[BoardType, list[str]] = {
        BoardType.AI: [
            "ai", "artificial intelligence", "machine learning", "ml",
            "deep learning", "neural network", "llm", "gpt", "transformer",
            "nlp", "computer vision", "reinforcement learning",
        ],
        BoardType.ENGINEERING: [
            "software", "engineering", "programming", "code", "developer",
            "devops", "kubernetes", "docker", "cloud", "api", "backend",
            "frontend", "database", "architecture", "microservice",
        ],
        BoardType.RESEARCH: [
            "research", "paper", "study", "experiment", "hypothesis",
            "methodology", "findings", "analysis", "arxiv", "journal",
            "conference", "peer review", "citation",
        ],
    }

    def __init__(
        self,
        *,
        clean_content: bool = True,
        infer_board_type: bool = True,
        calculate_quality: bool = True,
    ) -> None:
        """Initialize ContentNormalizer.

        Args:
            clean_content: Apply text cleaning.
            infer_board_type: Automatically infer board type.
            calculate_quality: Calculate quality score.
        """
        self._clean_content = clean_content
        self._infer_board_type = infer_board_type
        self._calculate_quality = calculate_quality

    def normalize(
        self,
        raw_item: RawItemDTO,
        parse_result: ParseResult,
        *,
        content_type: ContentType = ContentType.ARTICLE,
    ) -> NormalizedItemDTO:
        """Normalize parsed content into NormalizedItemDTO.

        Args:
            raw_item: Original raw item.
            parse_result: Result from parser.
            content_type: Content type hint.

        Returns:
            NormalizedItemDTO ready for storage.
        """
        # Clean content
        title = parse_result.title
        clean_text_content = parse_result.clean_text
        excerpt = parse_result.excerpt

        if self._clean_content:
            title = clean_title(title)
            clean_text_content = clean_text(clean_text_content)
            if excerpt:
                excerpt = clean_text(excerpt)

        # Infer board type
        board_type = BoardType.GENERAL
        if self._infer_board_type:
            board_type = self._infer_board(title, clean_text_content, parse_result.tags)

        # Calculate quality score
        quality_score = 0.0
        if self._calculate_quality:
            quality_score = self._calculate_quality_score(
                title, clean_text_content, parse_result
            )

        # Build canonical URL
        canonical_url = raw_item.canonical_url or raw_item.url

        # Build metadata
        metadata: dict[str, Any] = {
            "word_count": parse_result.word_count,
            "reading_time_minutes": parse_result.reading_time_minutes,
            "tags": parse_result.tags,
            "images": parse_result.images[:5],  # Limit images
            "links": parse_result.links[:10],  # Limit links
        }
        if parse_result.metadata:
            metadata.update(parse_result.metadata)

        return NormalizedItemDTO(
            raw_item_id=raw_item.id,
            source_id=raw_item.source_id,
            title=title,
            clean_text=clean_text_content,
            excerpt=excerpt or self._generate_excerpt(clean_text_content),
            author=parse_result.author,
            published_at=parse_result.published_at or datetime.now(timezone.utc),
            language=parse_result.language,
            content_type=content_type,
            board_type_candidate=board_type,
            quality_score=quality_score,
            ai_relevance_score=0.0,  # To be filled by AI scoring later
            canonical_url=canonical_url,
            metadata_json=metadata,
        )

    def _infer_board(
        self,
        title: str,
        text: str,
        tags: list[str],
    ) -> BoardType:
        """Infer board type from content."""
        combined = f"{title} {text} {' '.join(tags)}".lower()

        scores: dict[BoardType, int] = {
            BoardType.AI: 0,
            BoardType.ENGINEERING: 0,
            BoardType.RESEARCH: 0,
        }

        for board_type, keywords in self.BOARD_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined:
                    scores[board_type] += 1

        # Find highest scoring board
        max_score = max(scores.values())
        if max_score >= 2:  # Require at least 2 keyword matches
            for board_type, score in scores.items():
                if score == max_score:
                    return board_type

        return BoardType.GENERAL

    def _calculate_quality_score(
        self,
        title: str,
        text: str,
        parse_result: ParseResult,
    ) -> float:
        """Calculate quality score (0.0 to 1.0)."""
        score = 0.0
        max_score = 0.0

        # Title quality (0-20 points)
        max_score += 20
        if len(title) >= self.MIN_TITLE_LENGTH:
            score += 10
        if len(title) >= 30:
            score += 5
        if not title.isupper():  # Not all caps
            score += 5

        # Content length (0-30 points)
        max_score += 30
        word_count = parse_result.word_count
        if word_count >= self.MIN_WORD_COUNT:
            score += 10
        if word_count >= 200:
            score += 10
        if word_count >= 500:
            score += 10

        # Has author (0-10 points)
        max_score += 10
        if parse_result.author:
            score += 10

        # Has date (0-10 points)
        max_score += 10
        if parse_result.published_at:
            score += 10

        # Has images (0-10 points)
        max_score += 10
        if parse_result.images:
            score += 10

        # Has tags (0-10 points)
        max_score += 10
        if parse_result.tags:
            score += 5
        if len(parse_result.tags) >= 3:
            score += 5

        # Has excerpt (0-10 points)
        max_score += 10
        if parse_result.excerpt:
            score += 10

        return round(score / max_score, 2) if max_score > 0 else 0.0

    def _generate_excerpt(self, text: str, max_length: int = 200) -> str:
        """Generate excerpt from text."""
        if len(text) <= max_length:
            return text

        excerpt = text[:max_length]
        last_space = excerpt.rfind(" ")
        if last_space > max_length // 2:
            excerpt = excerpt[:last_space]

        return excerpt.rstrip(".,;:") + "..."


# Default instance
default_normalizer = ContentNormalizer()


def normalize_content(
    raw_item: RawItemDTO,
    parse_result: ParseResult,
    *,
    content_type: ContentType = ContentType.ARTICLE,
) -> NormalizedItemDTO:
    """Normalize content using default normalizer."""
    return default_normalizer.normalize(raw_item, parse_result, content_type=content_type)
