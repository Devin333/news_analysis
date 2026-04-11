"""Deduplication strategies for content items."""

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.normalized_item import NormalizedItemDTO

logger = get_logger(__name__)


@dataclass
class DedupResult:
    """Result of deduplication check."""

    is_duplicate: bool
    duplicate_of: int | None = None  # ID of the original item
    similarity_score: float = 0.0
    strategy: str = ""
    reason: str = ""


class DedupStrategy(ABC):
    """Abstract base class for deduplication strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        ...

    @abstractmethod
    def check(
        self,
        item: NormalizedItemDTO,
        existing_items: list[NormalizedItemDTO],
    ) -> DedupResult:
        """Check if item is a duplicate of any existing items.

        Args:
            item: New item to check.
            existing_items: List of existing items to compare against.

        Returns:
            DedupResult indicating if duplicate was found.
        """
        ...

    def compute_fingerprint(self, item: NormalizedItemDTO) -> str:
        """Compute a fingerprint for the item (optional)."""
        return ""


class URLDedupStrategy(DedupStrategy):
    """Deduplicate based on canonical URL."""

    @property
    def name(self) -> str:
        return "url"

    def check(
        self,
        item: NormalizedItemDTO,
        existing_items: list[NormalizedItemDTO],
    ) -> DedupResult:
        """Check for URL-based duplicates."""
        if not item.canonical_url:
            return DedupResult(is_duplicate=False, strategy=self.name)

        normalized_url = self._normalize_url(item.canonical_url)

        for existing in existing_items:
            if existing.canonical_url:
                existing_normalized = self._normalize_url(existing.canonical_url)
                if normalized_url == existing_normalized:
                    return DedupResult(
                        is_duplicate=True,
                        duplicate_of=existing.id,
                        similarity_score=1.0,
                        strategy=self.name,
                        reason=f"Same URL: {normalized_url}",
                    )

        return DedupResult(is_duplicate=False, strategy=self.name)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        # Remove protocol
        url = re.sub(r"^https?://", "", url.lower())
        # Remove www
        url = re.sub(r"^www\.", "", url)
        # Remove trailing slash
        url = url.rstrip("/")
        # Remove common tracking parameters
        url = re.sub(r"\?utm_[^&]+(&|$)", "", url)
        url = re.sub(r"[?&]ref=[^&]+", "", url)
        return url

    def compute_fingerprint(self, item: NormalizedItemDTO) -> str:
        """Compute URL-based fingerprint."""
        if item.canonical_url:
            return hashlib.md5(
                self._normalize_url(item.canonical_url).encode()
            ).hexdigest()
        return ""


class TitleDedupStrategy(DedupStrategy):
    """Deduplicate based on title similarity."""

    SIMILARITY_THRESHOLD = 0.9

    @property
    def name(self) -> str:
        return "title"

    def check(
        self,
        item: NormalizedItemDTO,
        existing_items: list[NormalizedItemDTO],
    ) -> DedupResult:
        """Check for title-based duplicates."""
        if not item.title:
            return DedupResult(is_duplicate=False, strategy=self.name)

        normalized_title = self._normalize_title(item.title)

        for existing in existing_items:
            if existing.title:
                existing_normalized = self._normalize_title(existing.title)
                similarity = self._compute_similarity(normalized_title, existing_normalized)

                if similarity >= self.SIMILARITY_THRESHOLD:
                    return DedupResult(
                        is_duplicate=True,
                        duplicate_of=existing.id,
                        similarity_score=similarity,
                        strategy=self.name,
                        reason=f"Similar title (score={similarity:.2f})",
                    )

        return DedupResult(is_duplicate=False, strategy=self.name)

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        # Lowercase
        title = title.lower()
        # Remove punctuation
        title = re.sub(r"[^\w\s]", "", title)
        # Normalize whitespace
        title = " ".join(title.split())
        return title

    def _compute_similarity(self, a: str, b: str) -> float:
        """Compute Jaccard similarity between two strings."""
        if not a or not b:
            return 0.0

        words_a = set(a.split())
        words_b = set(b.split())

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return intersection / union if union > 0 else 0.0

    def compute_fingerprint(self, item: NormalizedItemDTO) -> str:
        """Compute title-based fingerprint."""
        if item.title:
            normalized = self._normalize_title(item.title)
            return hashlib.md5(normalized.encode()).hexdigest()
        return ""


class ContentDedupStrategy(DedupStrategy):
    """Deduplicate based on content similarity using simhash-like approach."""

    SIMILARITY_THRESHOLD = 0.85
    SHINGLE_SIZE = 3

    @property
    def name(self) -> str:
        return "content"

    def check(
        self,
        item: NormalizedItemDTO,
        existing_items: list[NormalizedItemDTO],
    ) -> DedupResult:
        """Check for content-based duplicates."""
        if not item.clean_text or len(item.clean_text) < 100:
            return DedupResult(is_duplicate=False, strategy=self.name)

        item_shingles = self._get_shingles(item.clean_text)

        for existing in existing_items:
            if existing.clean_text and len(existing.clean_text) >= 100:
                existing_shingles = self._get_shingles(existing.clean_text)
                similarity = self._jaccard_similarity(item_shingles, existing_shingles)

                if similarity >= self.SIMILARITY_THRESHOLD:
                    return DedupResult(
                        is_duplicate=True,
                        duplicate_of=existing.id,
                        similarity_score=similarity,
                        strategy=self.name,
                        reason=f"Similar content (score={similarity:.2f})",
                    )

        return DedupResult(is_duplicate=False, strategy=self.name)

    def _get_shingles(self, text: str) -> set[str]:
        """Generate character n-gram shingles from text."""
        # Normalize text
        text = text.lower()
        text = re.sub(r"\s+", " ", text)

        # Generate shingles
        shingles: set[str] = set()
        for i in range(len(text) - self.SHINGLE_SIZE + 1):
            shingle = text[i : i + self.SHINGLE_SIZE]
            shingles.add(shingle)

        return shingles

    def _jaccard_similarity(self, a: set[str], b: set[str]) -> float:
        """Compute Jaccard similarity between two sets."""
        if not a or not b:
            return 0.0

        intersection = len(a & b)
        union = len(a | b)

        return intersection / union if union > 0 else 0.0

    def compute_fingerprint(self, item: NormalizedItemDTO) -> str:
        """Compute content-based fingerprint (simhash-like)."""
        if not item.clean_text:
            return ""

        # Simple fingerprint based on word frequencies
        words = item.clean_text.lower().split()[:100]  # First 100 words
        word_hash = hashlib.sha256(" ".join(sorted(set(words))).encode())
        return word_hash.hexdigest()[:32]


class CompositeDedupStrategy(DedupStrategy):
    """Combine multiple deduplication strategies."""

    def __init__(self, strategies: list[DedupStrategy] | None = None) -> None:
        """Initialize with list of strategies.

        Args:
            strategies: List of strategies to apply in order.
                       Defaults to URL, Title, Content strategies.
        """
        self._strategies = strategies or [
            URLDedupStrategy(),
            TitleDedupStrategy(),
            ContentDedupStrategy(),
        ]

    @property
    def name(self) -> str:
        return "composite"

    def check(
        self,
        item: NormalizedItemDTO,
        existing_items: list[NormalizedItemDTO],
    ) -> DedupResult:
        """Check using all strategies, return first match."""
        for strategy in self._strategies:
            result = strategy.check(item, existing_items)
            if result.is_duplicate:
                return result

        return DedupResult(is_duplicate=False, strategy=self.name)

    def compute_fingerprint(self, item: NormalizedItemDTO) -> str:
        """Compute combined fingerprint."""
        parts = []
        for strategy in self._strategies:
            fp = strategy.compute_fingerprint(item)
            if fp:
                parts.append(fp)
        return "|".join(parts)


class Deduplicator:
    """High-level deduplication service."""

    def __init__(self, strategy: DedupStrategy | None = None) -> None:
        """Initialize with a deduplication strategy.

        Args:
            strategy: Strategy to use. Defaults to CompositeDedupStrategy.
        """
        self._strategy = strategy or CompositeDedupStrategy()

    def is_duplicate(
        self,
        item: NormalizedItemDTO,
        existing_items: list[NormalizedItemDTO],
    ) -> DedupResult:
        """Check if item is a duplicate.

        Args:
            item: New item to check.
            existing_items: Existing items to compare against.

        Returns:
            DedupResult with duplicate information.
        """
        return self._strategy.check(item, existing_items)

    def filter_duplicates(
        self,
        items: list[NormalizedItemDTO],
        existing_items: list[NormalizedItemDTO] | None = None,
    ) -> tuple[list[NormalizedItemDTO], list[DedupResult]]:
        """Filter out duplicates from a list of items.

        Args:
            items: Items to filter.
            existing_items: Optional existing items to check against.

        Returns:
            Tuple of (unique items, duplicate results).
        """
        existing = list(existing_items) if existing_items else []
        unique: list[NormalizedItemDTO] = []
        duplicates: list[DedupResult] = []

        for item in items:
            # Check against existing and already-accepted unique items
            all_existing = existing + unique
            result = self.is_duplicate(item, all_existing)

            if result.is_duplicate:
                duplicates.append(result)
                logger.debug(f"Duplicate found: {result.reason}")
            else:
                unique.append(item)

        logger.info(
            f"Deduplication: {len(unique)} unique, {len(duplicates)} duplicates"
        )
        return unique, duplicates

    def compute_fingerprint(self, item: NormalizedItemDTO) -> str:
        """Compute fingerprint for an item."""
        return self._strategy.compute_fingerprint(item)


# Default instance
default_deduplicator = Deduplicator()


def is_duplicate(
    item: NormalizedItemDTO,
    existing_items: list[NormalizedItemDTO],
) -> DedupResult:
    """Check if item is duplicate using default deduplicator."""
    return default_deduplicator.is_duplicate(item, existing_items)


def filter_duplicates(
    items: list[NormalizedItemDTO],
    existing_items: list[NormalizedItemDTO] | None = None,
) -> tuple[list[NormalizedItemDTO], list[DedupResult]]:
    """Filter duplicates using default deduplicator."""
    return default_deduplicator.filter_duplicates(items, existing_items)
