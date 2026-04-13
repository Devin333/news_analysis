"""Content type classifier for identifying content types.

This module provides rule-based classification of content into
different types (article, blog, paper, repo, release, discussion, changelog).
"""

from dataclasses import dataclass
import re

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType, SourceType

logger = get_logger(__name__)


# URL patterns for content type detection
URL_PATTERNS = {
    ContentType.PAPER: [
        r"arxiv\.org",
        r"papers\.nips\.cc",
        r"openreview\.net",
        r"aclanthology\.org",
        r"proceedings\.mlr\.press",
        r"\.pdf$",
    ],
    ContentType.REPOSITORY: [
        r"github\.com/[^/]+/[^/]+$",
        r"gitlab\.com/[^/]+/[^/]+$",
        r"bitbucket\.org",
        r"huggingface\.co/[^/]+/[^/]+$",
    ],
    ContentType.DISCUSSION: [
        r"reddit\.com/r/",
        r"news\.ycombinator\.com",
        r"twitter\.com",
        r"x\.com",
        r"discord\.com",
        r"stackoverflow\.com",
    ],
}

# Title patterns for content type detection
TITLE_PATTERNS = {
    ContentType.PAPER: [
        r"^\[[\d\.]+\]",  # arXiv ID pattern
        r"paper:",
        r"research:",
        r"a survey",
        r"a study",
        r"towards",
        r"learning to",
        r"on the",
    ],
    ContentType.RELEASE: [
        r"v?\d+\.\d+",  # Version number
        r"release",
        r"released",
        r"launches",
        r"launched",
        r"announces",
        r"announced",
        r"introducing",
        r"now available",
    ],
    ContentType.CHANGELOG: [
        r"changelog",
        r"release notes",
        r"what's new",
        r"updates in",
        r"changes in",
    ],
    ContentType.BLOG: [
        r"blog:",
        r"how to",
        r"tutorial:",
        r"guide:",
        r"introduction to",
        r"getting started",
        r"deep dive",
    ],
}


@dataclass
class ContentTypeResult:
    """Result of content type classification."""

    content_type: ContentType
    confidence: float
    rationale: str
    source_hint: SourceType | None = None


@dataclass
class ContentTypeConfig:
    """Configuration for content type classifier."""

    # Minimum confidence to return a type
    min_confidence: float = 0.3

    # Default type when uncertain
    default_type: ContentType = ContentType.ARTICLE

    # Weight for URL pattern matches
    url_weight: float = 0.4

    # Weight for title pattern matches
    title_weight: float = 0.3

    # Weight for source type hints
    source_weight: float = 0.3


class ContentTypeClassifier:
    """Rule-based content type classifier.

    Classifies content into types based on:
    - URL patterns
    - Title patterns
    - Source type hints
    """

    def __init__(self, config: ContentTypeConfig | None = None) -> None:
        """Initialize the classifier.

        Args:
            config: Configuration for classification behavior.
        """
        self._config = config or ContentTypeConfig()
        self._compiled_url_patterns: dict[ContentType, list[re.Pattern]] = {}
        self._compiled_title_patterns: dict[ContentType, list[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns."""
        for content_type, patterns in URL_PATTERNS.items():
            self._compiled_url_patterns[content_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        for content_type, patterns in TITLE_PATTERNS.items():
            self._compiled_title_patterns[content_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def classify(
        self,
        *,
        title: str = "",
        url: str = "",
        source_type: SourceType | None = None,
        content_length: int = 0,
    ) -> ContentTypeResult:
        """Classify content type.

        Args:
            title: Content title.
            url: Content URL.
            source_type: Type of source.
            content_length: Length of content text.

        Returns:
            ContentTypeResult with classification details.
        """
        scores: dict[ContentType, float] = {ct: 0.0 for ct in ContentType}
        reasons: dict[ContentType, list[str]] = {ct: [] for ct in ContentType}

        # URL pattern matching
        if url:
            for content_type, patterns in self._compiled_url_patterns.items():
                for pattern in patterns:
                    if pattern.search(url):
                        scores[content_type] += self._config.url_weight
                        reasons[content_type].append(f"URL matches {pattern.pattern}")
                        break

        # Title pattern matching
        if title:
            for content_type, patterns in self._compiled_title_patterns.items():
                for pattern in patterns:
                    if pattern.search(title):
                        scores[content_type] += self._config.title_weight
                        reasons[content_type].append(f"title matches '{pattern.pattern}'")
                        break

        # Source type hints
        if source_type:
            source_type_map = {
                SourceType.ARXIV: ContentType.PAPER,
                SourceType.GITHUB: ContentType.REPOSITORY,
                SourceType.RSS: ContentType.ARTICLE,
                SourceType.WEB: ContentType.ARTICLE,
            }
            if source_type in source_type_map:
                mapped_type = source_type_map[source_type]
                scores[mapped_type] += self._config.source_weight
                reasons[mapped_type].append(f"source type is {source_type.value}")

        # Find best match
        best_type = self._config.default_type
        best_score = 0.0

        for content_type, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = content_type

        # Use default if confidence too low
        if best_score < self._config.min_confidence:
            best_type = self._config.default_type
            best_score = self._config.min_confidence
            reasons[best_type].append("default classification")

        # Build rationale
        rationale = "; ".join(reasons[best_type]) if reasons[best_type] else "default"

        result = ContentTypeResult(
            content_type=best_type,
            confidence=min(best_score, 1.0),
            rationale=rationale,
            source_hint=source_type,
        )

        logger.debug(
            f"Classified content as {best_type.value} "
            f"(confidence={result.confidence:.2f}): {rationale}"
        )

        return result

    def classify_from_item(
        self,
        item: "NormalizedItemDTO",
    ) -> ContentTypeResult:
        """Classify content type from a normalized item.

        Args:
            item: The normalized item.

        Returns:
            ContentTypeResult.
        """
        return self.classify(
            title=item.title,
            url=item.canonical_url or "",
            source_type=None,  # Would need source lookup
            content_length=len(item.clean_text) if item.clean_text else 0,
        )


# Singleton instance
_default_classifier: ContentTypeClassifier | None = None


def get_content_type_classifier() -> ContentTypeClassifier:
    """Get the default content type classifier.

    Returns:
        The default ContentTypeClassifier instance.
    """
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = ContentTypeClassifier()
    return _default_classifier


# Type hint for lazy import
if False:  # TYPE_CHECKING
    from app.contracts.dto.normalized_item import NormalizedItemDTO
