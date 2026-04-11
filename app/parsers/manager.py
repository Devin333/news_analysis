"""Parser manager for orchestrating parsing execution."""

import time
from dataclasses import dataclass, field
from typing import Any

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.parsers.base import BaseParser
from app.parsers.registry import ParserRegistry, get_parser_registry

logger = get_logger(__name__)


@dataclass
class ParseJobResult:
    """Result of parsing multiple raw items."""

    total: int = 0
    success_count: int = 0
    failure_count: int = 0
    skipped_count: int = 0
    duration_seconds: float = 0.0
    results: list[tuple[int, ParseResult]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ParserManager:
    """Manages parser execution and orchestration.

    Responsibilities:
    - Look up the correct parser for a content type.
    - Execute parsing with error handling.
    - Provide batch parsing across multiple raw items.
    """

    def __init__(self, registry: ParserRegistry | None = None) -> None:
        """Initialize with an optional custom registry.

        Args:
            registry: ParserRegistry to use. Defaults to global registry.
        """
        self._registry = registry or get_parser_registry()

    @property
    def registry(self) -> ParserRegistry:
        """Access the underlying registry."""
        return self._registry

    def parse_item(
        self,
        raw_item: RawItemDTO,
        content_type: ContentType = ContentType.ARTICLE,
    ) -> ParseResult:
        """Parse a single raw item.

        Args:
            raw_item: RawItemDTO to parse.
            content_type: ContentType hint for parser selection.

        Returns:
            ParseResult with extracted content or error.
        """
        parser = self._registry.get(content_type)
        if parser is None:
            logger.warning(f"No parser registered for {content_type}")
            return ParseResult.failure(f"No parser for content type: {content_type}")

        if not parser.can_parse(raw_item):
            logger.debug(f"Parser {parser.name} cannot parse item {raw_item.id}")
            return ParseResult.failure(f"Parser {parser.name} cannot handle this item")

        try:
            result = parser.parse(raw_item)
            if result.success:
                logger.debug(
                    f"Parsed item {raw_item.id} with {parser.name}: "
                    f"{result.word_count} words"
                )
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Parser {parser.name} failed for item {raw_item.id}: {exc}")
            return ParseResult.failure(str(exc))

    def parse_many(
        self,
        raw_items: list[RawItemDTO],
        content_type: ContentType = ContentType.ARTICLE,
        *,
        stop_on_error: bool = False,
    ) -> ParseJobResult:
        """Parse multiple raw items.

        Args:
            raw_items: List of RawItemDTO to parse.
            content_type: ContentType hint for parser selection.
            stop_on_error: If True, stop on first failure.

        Returns:
            ParseJobResult with aggregated results.
        """
        start = time.monotonic()
        job_result = ParseJobResult(total=len(raw_items))

        for raw_item in raw_items:
            if raw_item.id is None:
                job_result.skipped_count += 1
                continue

            result = self.parse_item(raw_item, content_type)
            job_result.results.append((raw_item.id, result))

            if result.success:
                job_result.success_count += 1
            else:
                job_result.failure_count += 1
                if result.error:
                    job_result.errors.append(f"Item {raw_item.id}: {result.error}")
                if stop_on_error:
                    logger.warning(f"Stopping batch parse due to error on item {raw_item.id}")
                    break

        job_result.duration_seconds = time.monotonic() - start
        logger.info(
            f"Parsed {job_result.success_count}/{job_result.total} items "
            f"in {job_result.duration_seconds:.3f}s"
        )
        return job_result

    def supports(self, content_type: ContentType) -> bool:
        """Check if a parser is available for the given type."""
        return self._registry.has(content_type)
