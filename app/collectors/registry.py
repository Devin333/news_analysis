"""Collector registry for mapping SourceType to collector instances."""

from app.bootstrap.logging import get_logger
from app.collectors.base import BaseCollector
from app.common.enums import SourceType

logger = get_logger(__name__)


class CollectorRegistry:
    """Registry that maps SourceType to collector instances.

    Usage:
        registry = CollectorRegistry()
        registry.register(RSSCollector())
        collector = registry.get(SourceType.RSS)
    """

    def __init__(self) -> None:
        self._collectors: dict[SourceType, BaseCollector] = {}

    def register(self, collector: BaseCollector) -> None:
        """Register a collector for its supported types.

        Args:
            collector: A BaseCollector instance.
        """
        for source_type in collector.supported_types:
            if source_type in self._collectors:
                logger.warning(
                    f"Overwriting collector for {source_type}: "
                    f"{self._collectors[source_type].name} -> {collector.name}"
                )
            self._collectors[source_type] = collector
            logger.info(f"Registered collector {collector.name} for {source_type}")

    def get(self, source_type: SourceType) -> BaseCollector | None:
        """Get the collector for a given source type.

        Args:
            source_type: The SourceType to look up.

        Returns:
            The registered collector or None if not found.
        """
        return self._collectors.get(source_type)

    def has(self, source_type: SourceType) -> bool:
        """Check if a collector is registered for the given type."""
        return source_type in self._collectors

    def list_types(self) -> list[SourceType]:
        """Return all registered source types."""
        return list(self._collectors.keys())

    def list_collectors(self) -> list[BaseCollector]:
        """Return all unique registered collectors."""
        seen: set[int] = set()
        result: list[BaseCollector] = []
        for collector in self._collectors.values():
            if id(collector) not in seen:
                seen.add(id(collector))
                result.append(collector)
        return result


# Global default registry instance
_default_registry: CollectorRegistry | None = None


def get_registry() -> CollectorRegistry:
    """Get or create the default global registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = CollectorRegistry()
    return _default_registry


def register_collector(collector: BaseCollector) -> None:
    """Convenience function to register a collector in the default registry."""
    get_registry().register(collector)
