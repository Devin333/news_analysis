"""Collector manager for orchestrating collection execution."""

import time
from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.collectors.registry import CollectorRegistry, get_registry
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest, CollectResult

if TYPE_CHECKING:
    from app.contracts.dto.source import SourceRead

logger = get_logger(__name__)


class CollectorManager:
    """Manages collector execution and orchestration.

    Responsibilities:
    - Look up the correct collector for a source type.
    - Execute collection with error handling.
    - Provide batch collection across multiple sources.
    """

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize with an optional custom registry.

        Args:
            registry: CollectorRegistry to use. Defaults to global registry.
        """
        self._registry = registry or get_registry()

    @property
    def registry(self) -> CollectorRegistry:
        """Access the underlying registry."""
        return self._registry

    async def collect_source(self, source: "SourceRead") -> CollectResult:
        """Execute collection for a single source.

        Args:
            source: SourceRead DTO with source details.

        Returns:
            CollectResult with items or error.
        """
        start = time.monotonic()
        source_type = source.source_type

        collector = self._registry.get(source_type)
        if collector is None:
            logger.warning(f"No collector registered for {source_type}")
            return CollectResult(
                source_id=source.id,
                success=False,
                error=f"No collector for source type: {source_type}",
                duration_seconds=time.monotonic() - start,
            )

        request = CollectRequest(
            source_id=source.id,
            source_type=source_type,
            base_url=source.base_url,
            feed_url=source.feed_url,
            metadata_json=source.metadata_json,
        )

        # Validate
        validation_error = await collector.validate(request)
        if validation_error:
            logger.warning(f"Validation failed for source {source.id}: {validation_error}")
            return CollectResult(
                source_id=source.id,
                success=False,
                error=validation_error,
                duration_seconds=time.monotonic() - start,
            )

        # Execute
        try:
            result = await collector.collect(request)
            result.duration_seconds = time.monotonic() - start
            logger.info(
                f"Collected {len(result.items)} items from source {source.id} "
                f"in {result.duration_seconds:.3f}s"
            )
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Collection failed for source {source.id}: {exc}")
            return CollectResult(
                source_id=source.id,
                success=False,
                error=str(exc),
                duration_seconds=time.monotonic() - start,
            )

    async def collect_many(
        self,
        sources: list["SourceRead"],
        *,
        stop_on_error: bool = False,
    ) -> list[CollectResult]:
        """Execute collection for multiple sources sequentially.

        Args:
            sources: List of SourceRead DTOs.
            stop_on_error: If True, stop on first failure.

        Returns:
            List of CollectResult, one per source.
        """
        results: list[CollectResult] = []
        for source in sources:
            result = await self.collect_source(source)
            results.append(result)
            if stop_on_error and not result.success:
                logger.warning(f"Stopping batch collection due to error on source {source.id}")
                break
        return results

    def supports(self, source_type: SourceType) -> bool:
        """Check if a collector is available for the given type."""
        return self._registry.has(source_type)
