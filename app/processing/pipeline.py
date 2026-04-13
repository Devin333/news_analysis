"""Processing pipeline for raw items to normalized items."""

import time
from dataclasses import dataclass, field
from typing import Any

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.parsers.base import BaseParser
from app.parsers.html import HTMLParser
from app.parsers.json_parser import JSONParser
from app.parsers.manager import ParserManager
from app.parsers.registry import ParserRegistry
from app.parsers.rss import RSSParser
from app.processing.dedup import Deduplicator, DedupResult, filter_duplicates
from app.processing.normalizer import ContentNormalizer, normalize_content

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Result of processing pipeline execution."""

    total_input: int = 0
    parsed_count: int = 0
    normalized_count: int = 0
    deduplicated_count: int = 0
    failed_count: int = 0
    duration_seconds: float = 0.0
    items: list[NormalizedItemDTO] = field(default_factory=list)
    duplicates: list[DedupResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ProcessingPipeline:
    """End-to-end pipeline for processing raw items.

    Pipeline stages:
    1. Parse: Extract structured content from raw items
    2. Normalize: Clean and standardize content
    3. Deduplicate: Remove duplicate items
    4. Output: Return normalized items ready for storage
    """

    def __init__(
        self,
        parser_registry: ParserRegistry | None = None,
        normalizer: ContentNormalizer | None = None,
        deduplicator: Deduplicator | None = None,
    ) -> None:
        """Initialize pipeline with optional custom components.

        Args:
            parser_registry: Custom parser registry.
            normalizer: Custom content normalizer.
            deduplicator: Custom deduplicator.
        """
        # Setup parser registry with default parsers
        self._parser_registry = parser_registry or self._create_default_registry()
        self._parser_manager = ParserManager(self._parser_registry)
        self._normalizer = normalizer or ContentNormalizer()
        self._deduplicator = deduplicator or Deduplicator()

    def _create_default_registry(self) -> ParserRegistry:
        """Create default parser registry with all built-in parsers."""
        registry = ParserRegistry()
        # HTMLParser handles ARTICLE and THREAD, set as default
        registry.register(HTMLParser(), as_default=True)
        # JSONParser handles REPOSITORY and PAPER
        registry.register(JSONParser())
        # RSSParser is used internally for JSON-based RSS entries
        # Not registered to avoid conflicts - used directly when raw_json is present
        return registry

    def process(
        self,
        raw_items: list[RawItemDTO],
        *,
        content_type: ContentType = ContentType.ARTICLE,
        existing_items: list[NormalizedItemDTO] | None = None,
        skip_dedup: bool = False,
    ) -> PipelineResult:
        """Process raw items through the full pipeline.

        Args:
            raw_items: List of raw items to process.
            content_type: Content type hint for parsing.
            existing_items: Existing items for deduplication.
            skip_dedup: Skip deduplication step.

        Returns:
            PipelineResult with processed items and statistics.
        """
        start = time.monotonic()
        result = PipelineResult(total_input=len(raw_items))

        if not raw_items:
            result.duration_seconds = time.monotonic() - start
            return result

        logger.info(f"Starting pipeline for {len(raw_items)} items")

        # Stage 1: Parse
        parsed_items: list[tuple[RawItemDTO, ParseResult]] = []
        for raw_item in raw_items:
            parse_result = self._parse_item(raw_item, content_type)
            if parse_result.success:
                parsed_items.append((raw_item, parse_result))
                result.parsed_count += 1
            else:
                result.failed_count += 1
                if parse_result.error:
                    result.errors.append(f"Parse failed for item {raw_item.id}: {parse_result.error}")

        logger.info(f"Parsed {result.parsed_count}/{len(raw_items)} items")

        # Stage 2: Normalize
        normalized_items: list[NormalizedItemDTO] = []
        for raw_item, parse_result in parsed_items:
            try:
                normalized = self._normalizer.normalize(
                    raw_item, parse_result, content_type=content_type
                )
                normalized_items.append(normalized)
                result.normalized_count += 1
            except Exception as exc:  # noqa: BLE001
                result.failed_count += 1
                result.errors.append(f"Normalize failed for item {raw_item.id}: {exc}")

        logger.info(f"Normalized {result.normalized_count} items")

        # Stage 3: Deduplicate
        if skip_dedup:
            result.items = normalized_items
            result.deduplicated_count = len(normalized_items)
        else:
            unique, duplicates = self._deduplicator.filter_duplicates(
                normalized_items, existing_items
            )
            result.items = unique
            result.duplicates = duplicates
            result.deduplicated_count = len(unique)
            logger.info(f"Deduplicated: {len(unique)} unique, {len(duplicates)} duplicates")

        result.duration_seconds = time.monotonic() - start
        logger.info(
            f"Pipeline completed in {result.duration_seconds:.3f}s: "
            f"{result.deduplicated_count} items ready"
        )

        return result

    def _parse_item(
        self,
        raw_item: RawItemDTO,
        content_type: ContentType,
    ) -> ParseResult:
        """Parse a single raw item with appropriate parser."""
        # Determine best parser based on content
        if raw_item.raw_json:
            # If raw_json contains a "title" key it likely came from an RSS
            # collector that preserved entry metadata.  Use the dedicated
            # RSSParser so the title / author / tags are extracted properly.
            if "title" in raw_item.raw_json:
                rss_parser = RSSParser()
                result = rss_parser.parse(raw_item)
                if result.success:
                    return result

            # Other JSON content - use JSON parser (e.g. GitHub / arXiv)
            parser = self._parser_registry.get(ContentType.REPOSITORY)
            if parser and parser.can_parse(raw_item):
                return parser.parse(raw_item)

        if raw_item.raw_html:
            # HTML content - use HTML parser
            parser = self._parser_registry.get(ContentType.ARTICLE)
            if parser and parser.can_parse(raw_item):
                result = parser.parse(raw_item)
                # If HTML parser couldn't extract a title but raw_json has one,
                # patch it in so downstream normalisation gets a usable title.
                if result.success and not result.title and raw_item.raw_json:
                    result.title = raw_item.raw_json.get("title", "")
                return result

        # Fallback to default parser
        return self._parser_manager.parse_item(raw_item, content_type)

    def process_single(
        self,
        raw_item: RawItemDTO,
        *,
        content_type: ContentType = ContentType.ARTICLE,
    ) -> tuple[NormalizedItemDTO | None, ParseResult]:
        """Process a single raw item (no deduplication).

        Args:
            raw_item: Raw item to process.
            content_type: Content type hint.

        Returns:
            Tuple of (normalized item or None, parse result).
        """
        parse_result = self._parse_item(raw_item, content_type)

        if not parse_result.success:
            return None, parse_result

        try:
            normalized = self._normalizer.normalize(
                raw_item, parse_result, content_type=content_type
            )
            return normalized, parse_result
        except Exception as exc:  # noqa: BLE001
            return None, ParseResult.failure(str(exc))


# Default pipeline instance
default_pipeline = ProcessingPipeline()


def process_raw_items(
    raw_items: list[RawItemDTO],
    *,
    content_type: ContentType = ContentType.ARTICLE,
    existing_items: list[NormalizedItemDTO] | None = None,
    skip_dedup: bool = False,
) -> PipelineResult:
    """Process raw items using default pipeline."""
    return default_pipeline.process(
        raw_items,
        content_type=content_type,
        existing_items=existing_items,
        skip_dedup=skip_dedup,
    )


def process_single_item(
    raw_item: RawItemDTO,
    *,
    content_type: ContentType = ContentType.ARTICLE,
) -> tuple[NormalizedItemDTO | None, ParseResult]:
    """Process single item using default pipeline."""
    return default_pipeline.process_single(raw_item, content_type=content_type)
