"""RSS Collector implementation using feedparser."""

import hashlib
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser

from app.bootstrap.logging import get_logger
from app.collectors.base import BaseCollector
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest, CollectResult, RawCollectedItem

logger = get_logger(__name__)


class RSSCollector(BaseCollector):
    """Collector for RSS/Atom feeds using feedparser."""

    @property
    def supported_types(self) -> list[SourceType]:
        return [SourceType.RSS]

    async def validate(self, request: CollectRequest) -> str | None:
        """Validate that feed_url is provided."""
        base_error = await super().validate(request)
        if base_error:
            return base_error
        if not request.feed_url:
            return "RSS collector requires feed_url"
        return None

    async def collect(self, request: CollectRequest) -> CollectResult:
        """Fetch and parse RSS feed, returning raw items."""
        start = time.monotonic()
        feed_url = request.feed_url

        if not feed_url:
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error="feed_url is required",
                duration_seconds=time.monotonic() - start,
            )

        logger.info(f"Fetching RSS feed: {feed_url}")

        try:
            # feedparser is synchronous; in production consider running in executor
            feed = feedparser.parse(feed_url)

            if feed.bozo and feed.bozo_exception:
                # Feed had parsing issues but may still have entries
                logger.warning(f"Feed parse warning: {feed.bozo_exception}")

            items = self._extract_items(feed, request)
            items = items[: request.max_items]

            return CollectResult(
                source_id=request.source_id,
                success=True,
                items=items,
                duration_seconds=time.monotonic() - start,
                metadata={
                    "feed_title": feed.feed.get("title", ""),
                    "feed_link": feed.feed.get("link", ""),
                    "entry_count": len(feed.entries),
                },
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(f"RSS collection failed for {feed_url}: {exc}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=str(exc),
                duration_seconds=time.monotonic() - start,
            )

    def _extract_items(
        self, feed: feedparser.FeedParserDict, request: CollectRequest
    ) -> list[RawCollectedItem]:
        """Convert feedparser entries to RawCollectedItem list."""
        items: list[RawCollectedItem] = []

        for entry in feed.entries:
            item = self._entry_to_item(entry, request.source_id)
            if item:
                items.append(item)

        return items

    def _entry_to_item(
        self, entry: dict[str, Any], source_id: int
    ) -> RawCollectedItem | None:
        """Convert a single feedparser entry to RawCollectedItem."""
        # Extract URL
        url = entry.get("link") or entry.get("id")
        if not url:
            return None

        # External ID: prefer entry id, fallback to URL hash
        external_id = entry.get("id") or self._hash_url(url)

        # Title
        title = entry.get("title", "")

        # Content: prefer content, fallback to summary
        raw_html = None
        raw_text = None
        if "content" in entry and entry["content"]:
            content_item = entry["content"][0]
            if content_item.get("type", "").startswith("text/html"):
                raw_html = content_item.get("value", "")
            else:
                raw_text = content_item.get("value", "")
        elif "summary" in entry:
            raw_html = entry["summary"]

        # Published date
        published_at = self._parse_date(entry)

        # Author
        author = entry.get("author") or entry.get("author_detail", {}).get("name")

        # Extra metadata
        extra: dict[str, Any] = {}
        if "tags" in entry:
            extra["tags"] = [t.get("term") for t in entry["tags"] if t.get("term")]
        if "enclosures" in entry:
            extra["enclosures"] = [
                {"url": e.get("href"), "type": e.get("type"), "length": e.get("length")}
                for e in entry["enclosures"]
            ]

        return RawCollectedItem(
            external_id=external_id,
            url=url,
            canonical_url=url,
            title=title,
            raw_html=raw_html,
            raw_text=raw_text,
            published_at=published_at,
            author=author,
            extra=extra,
        )

    def _parse_date(self, entry: dict[str, Any]) -> datetime | None:
        """Parse published date from entry."""
        # Try parsed struct first
        for key in ("published_parsed", "updated_parsed"):
            parsed = entry.get(key)
            if parsed:
                try:
                    return datetime(*parsed[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    pass

        # Try raw string
        for key in ("published", "updated"):
            raw = entry.get(key)
            if raw:
                try:
                    return parsedate_to_datetime(raw)
                except (TypeError, ValueError):
                    pass

        return None

    @staticmethod
    def _hash_url(url: str) -> str:
        """Generate a short hash for URL as fallback external_id."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
