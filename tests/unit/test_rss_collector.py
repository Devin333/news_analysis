"""Unit tests for RSSCollector."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.collectors.rss import RSSCollector
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest


@pytest.fixture
def rss_collector() -> RSSCollector:
    """Create an RSSCollector instance."""
    return RSSCollector()


@pytest.fixture
def valid_request() -> CollectRequest:
    """Create a valid RSS collect request."""
    return CollectRequest(
        source_id=1,
        source_type=SourceType.RSS,
        feed_url="https://example.com/feed.xml",
        max_items=10,
    )


class TestRSSCollectorProperties:
    """Tests for RSSCollector properties."""

    def test_supported_types(self, rss_collector: RSSCollector) -> None:
        """RSSCollector supports RSS type."""
        assert rss_collector.supported_types == [SourceType.RSS]

    def test_name(self, rss_collector: RSSCollector) -> None:
        """Name defaults to class name."""
        assert rss_collector.name == "RSSCollector"


class TestRSSCollectorValidation:
    """Tests for RSSCollector validation."""

    async def test_validate_success(
        self, rss_collector: RSSCollector, valid_request: CollectRequest
    ) -> None:
        """Validation passes with valid request."""
        result = await rss_collector.validate(valid_request)
        assert result is None

    async def test_validate_missing_feed_url(self, rss_collector: RSSCollector) -> None:
        """Validation fails without feed_url."""
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.RSS,
            feed_url=None,
        )
        result = await rss_collector.validate(request)
        assert result is not None
        assert "feed_url" in result

    async def test_validate_wrong_type(self, rss_collector: RSSCollector) -> None:
        """Validation fails for non-RSS type."""
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.WEB,
            feed_url="https://example.com/feed.xml",
        )
        result = await rss_collector.validate(request)
        assert result is not None
        assert "does not support" in result


class TestRSSCollectorCollect:
    """Tests for RSSCollector.collect()."""

    async def test_collect_missing_feed_url(self, rss_collector: RSSCollector) -> None:
        """Collect fails gracefully without feed_url."""
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.RSS,
            feed_url=None,
        )
        result = await rss_collector.collect(request)
        assert result.success is False
        assert result.error is not None
        assert "feed_url" in result.error

    async def test_collect_success(
        self, rss_collector: RSSCollector, valid_request: CollectRequest
    ) -> None:
        """Collect returns items from mocked feed."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feed.feed = {"title": "Test Feed", "link": "https://example.com"}
        mock_feed.entries = [
            {
                "id": "entry-1",
                "link": "https://example.com/article1",
                "title": "Article One",
                "summary": "<p>Summary content</p>",
                "published_parsed": (2026, 4, 10, 12, 0, 0, 0, 0, 0),
                "author": "John Doe",
            },
            {
                "id": "entry-2",
                "link": "https://example.com/article2",
                "title": "Article Two",
                "content": [{"type": "text/html", "value": "<p>Full content</p>"}],
            },
        ]

        with patch("app.collectors.rss.feedparser.parse", return_value=mock_feed):
            result = await rss_collector.collect(valid_request)

        assert result.success is True
        assert len(result.items) == 2
        assert result.items[0].external_id == "entry-1"
        assert result.items[0].title == "Article One"
        assert result.items[0].author == "John Doe"
        assert result.items[0].raw_html == "<p>Summary content</p>"
        assert result.items[1].raw_html == "<p>Full content</p>"
        assert result.metadata["feed_title"] == "Test Feed"

    async def test_collect_respects_max_items(
        self, rss_collector: RSSCollector
    ) -> None:
        """Collect limits items to max_items."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.bozo_exception = None
        mock_feed.feed = {}
        mock_feed.entries = [
            {"id": f"entry-{i}", "link": f"https://example.com/{i}", "title": f"Item {i}"}
            for i in range(20)
        ]

        request = CollectRequest(
            source_id=1,
            source_type=SourceType.RSS,
            feed_url="https://example.com/feed.xml",
            max_items=5,
        )

        with patch("app.collectors.rss.feedparser.parse", return_value=mock_feed):
            result = await rss_collector.collect(request)

        assert result.success is True
        assert len(result.items) == 5

    async def test_collect_handles_bozo_warning(
        self, rss_collector: RSSCollector, valid_request: CollectRequest
    ) -> None:
        """Collect continues with warning on bozo feed."""
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("XML parse warning")
        mock_feed.feed = {}
        mock_feed.entries = [
            {"id": "entry-1", "link": "https://example.com/1", "title": "Item"}
        ]

        with patch("app.collectors.rss.feedparser.parse", return_value=mock_feed):
            result = await rss_collector.collect(valid_request)

        assert result.success is True
        assert len(result.items) == 1

    async def test_collect_handles_exception(
        self, rss_collector: RSSCollector, valid_request: CollectRequest
    ) -> None:
        """Collect returns error on exception."""
        with patch(
            "app.collectors.rss.feedparser.parse",
            side_effect=RuntimeError("Network error"),
        ):
            result = await rss_collector.collect(valid_request)

        assert result.success is False
        assert result.error is not None
        assert "Network error" in result.error


class TestRSSCollectorHelpers:
    """Tests for RSSCollector helper methods."""

    def test_hash_url(self) -> None:
        """_hash_url produces consistent short hash."""
        url = "https://example.com/article"
        hash1 = RSSCollector._hash_url(url)
        hash2 = RSSCollector._hash_url(url)
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_parse_date_from_parsed(self, rss_collector: RSSCollector) -> None:
        """_parse_date extracts from parsed struct."""
        entry = {"published_parsed": (2026, 4, 10, 14, 30, 0, 0, 0, 0)}
        result = rss_collector._parse_date(entry)
        assert result is not None
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 10

    def test_parse_date_returns_none_for_missing(
        self, rss_collector: RSSCollector
    ) -> None:
        """_parse_date returns None when no date available."""
        entry = {}
        result = rss_collector._parse_date(entry)
        assert result is None

    def test_entry_to_item_skips_no_url(self, rss_collector: RSSCollector) -> None:
        """_entry_to_item returns None for entry without URL."""
        entry = {"title": "No Link Entry"}
        result = rss_collector._entry_to_item(entry, source_id=1)
        assert result is None

    def test_entry_to_item_extracts_tags(self, rss_collector: RSSCollector) -> None:
        """_entry_to_item extracts tags into extra."""
        entry = {
            "link": "https://example.com/1",
            "title": "Tagged",
            "tags": [{"term": "python"}, {"term": "news"}],
        }
        result = rss_collector._entry_to_item(entry, source_id=1)
        assert result is not None
        assert result.extra["tags"] == ["python", "news"]
