"""Collectors package for fetching content from various sources."""

from app.collectors.arxiv import ArxivCollector
from app.collectors.base import BaseCollector
from app.collectors.github import GitHubCollector
from app.collectors.manager import CollectorManager
from app.collectors.registry import CollectorRegistry, get_registry, register_collector
from app.collectors.rss import RSSCollector
from app.collectors.web import WebPageCollector

__all__ = [
    "ArxivCollector",
    "BaseCollector",
    "CollectorManager",
    "CollectorRegistry",
    "GitHubCollector",
    "RSSCollector",
    "WebPageCollector",
    "get_registry",
    "register_collector",
]
