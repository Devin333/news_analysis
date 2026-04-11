"""Collector initialization - register all collectors on startup."""

from app.bootstrap.logging import get_logger
from app.collectors.arxiv import ArxivCollector
from app.collectors.github import GitHubCollector
from app.collectors.registry import get_registry, register_collector
from app.collectors.rss import RSSCollector
from app.collectors.web import WebPageCollector

logger = get_logger(__name__)


def setup_collectors() -> None:
    """Register all built-in collectors with the global registry.

    Call this during application startup to ensure collectors are available
    for the collect job.
    """
    logger.info("Setting up collectors...")

    # Register all built-in collectors
    register_collector(RSSCollector())
    register_collector(WebPageCollector())
    register_collector(GitHubCollector())
    register_collector(ArxivCollector())

    registry = get_registry()
    types = registry.list_types()
    logger.info(f"Registered collectors for: {[t.value for t in types]}")
