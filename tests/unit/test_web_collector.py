"""Unit tests for WebPageCollector."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.web import WebPageCollector
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page Title</title>
    <meta name="description" content="A test page description">
    <meta name="author" content="Jane Doe">
    <meta property="article:published_time" content="2026-04-10T12:00:00+00:00">
    <link rel="canonical" href="https://example.com/canonical">
</head>
<body>
    <h1>Hello World</h1>
    <p>This is the main content of the page.</p>
    <a href="/article/1">Article 1</a>
    <a href="/article/2">Article 2</a>
    <a href="/tag/python">Tag Page</a>
    <a href="https://other.com/page">External Link</a>
</body>
</html>"""


@pytest.fixture
def web_collector() -> WebPageCollector:
    """Create a WebPageCollector instance."""
    return WebPageCollector(timeout=10.0, follow_links=False)


@pytest.fixture
def web_collector_with_links() -> WebPageCollector:
    """Create a WebPageCollector with link following enabled."""
    return WebPageCollector(timeout=10.0, follow_links=True, max_depth=1)


@pytest.fixture
def valid_request() -> CollectRequest:
    """Create a valid WEB collect request."""
    return CollectRequest(
        source_id=1,
        source_type=SourceType.WEB,
        base_url="https://example.com",
        max_items=10,
    )


class TestWebPageCollectorProperties:
    """Tests for WebPageCollector properties."""

    def test_supported_types(self, web_collector: WebPageCollector) -> None:
        """WebPageCollector supports WEB type."""
        assert web_collector.supported_types == [SourceType.WEB]

    def test_name(self, web_collector: WebPageCollector) -> None:
        """Name defaults to class name."""
        assert web_collector.name == "WebPageCollector"


class TestWebPageCollectorValidation:
    """Tests for WebPageCollector validation."""

    async def test_validate_success(
        self, web_collector: WebPageCollector, valid_request: CollectRequest
    ) -> None:
        """Validation passes with valid request."""
        result = await web_collector.validate(valid_request)
        assert result is None

    async def test_validate_missing_base_url(self, web_collector: WebPageCollector) -> None:
        """Validation fails without base_url."""
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.WEB,
            base_url=None,
        )
        result = await web_collector.validate(request)
        assert result is not None
        assert "base_url" in result

    async def test_validate_wrong_type(self, web_collector: WebPageCollector) -> None:
        """Validation fails for non-WEB type."""
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.RSS,
            base_url="https://example.com",
        )
        result = await web_collector.validate(request)
        assert result is not None
        assert "does not support" in result


class TestWebPageCollectorCollect:
    """Tests for WebPageCollector.collect()."""

    async def test_collect_missing_base_url(self, web_collector: WebPageCollector) -> None:
        """Collect fails gracefully without base_url."""
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.WEB,
            base_url=None,
        )
        result = await web_collector.collect(request)
        assert result.success is False
        assert result.error is not None
        assert "base_url" in result.error

    async def test_collect_success(
        self, web_collector: WebPageCollector, valid_request: CollectRequest
    ) -> None:
        """Collect returns items from mocked HTTP response."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.web.httpx.AsyncClient", return_value=mock_client):
            result = await web_collector.collect(valid_request)

        assert result.success is True
        assert len(result.items) == 1
        item = result.items[0]
        assert item.title == "Test Page Title"
        assert item.url == "https://example.com"
        assert item.canonical_url == "https://example.com/canonical"
        assert item.author == "Jane Doe"
        assert item.extra.get("description") == "A test page description"
        assert item.published_at is not None
        assert item.published_at.year == 2026

    async def test_collect_timeout(
        self, web_collector: WebPageCollector, valid_request: CollectRequest
    ) -> None:
        """Collect returns error on timeout."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.web.httpx.AsyncClient", return_value=mock_client):
            result = await web_collector.collect(valid_request)

        assert result.success is False
        assert result.error is not None
        assert "timeout" in result.error.lower()

    async def test_collect_http_error(
        self, web_collector: WebPageCollector, valid_request: CollectRequest
    ) -> None:
        """Collect returns error on HTTP error."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_response
            )
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.web.httpx.AsyncClient", return_value=mock_client):
            result = await web_collector.collect(valid_request)

        assert result.success is False
        assert result.error is not None
        assert "404" in result.error


class TestWebPageCollectorHelpers:
    """Tests for WebPageCollector helper methods."""

    def test_hash_url(self) -> None:
        """_hash_url produces consistent short hash."""
        url = "https://example.com/page"
        hash1 = WebPageCollector._hash_url(url)
        hash2 = WebPageCollector._hash_url(url)
        assert hash1 == hash2
        assert len(hash1) == 16

    def test_extract_links(self, web_collector: WebPageCollector) -> None:
        """_extract_links returns same-domain article links."""
        links = web_collector._extract_links(SAMPLE_HTML, "https://example.com")
        assert "https://example.com/article/1" in links
        assert "https://example.com/article/2" in links
        # Tag page should be filtered out
        assert not any("/tag/" in link for link in links)
        # External link should be filtered out
        assert not any("other.com" in link for link in links)

    def test_extract_publish_date(self, web_collector: WebPageCollector) -> None:
        """_extract_publish_date extracts from meta tags."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
        date = web_collector._extract_publish_date(soup)
        assert date is not None
        assert date.year == 2026
        assert date.month == 4

    def test_extract_publish_date_missing(self, web_collector: WebPageCollector) -> None:
        """_extract_publish_date returns None when no date meta."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup("<html><body>No date</body></html>", "html.parser")
        date = web_collector._extract_publish_date(soup)
        assert date is None

    def test_html_to_item(self, web_collector: WebPageCollector) -> None:
        """_html_to_item extracts all fields correctly."""
        item = web_collector._html_to_item(
            "https://example.com", SAMPLE_HTML, source_id=1
        )
        assert item is not None
        assert item.title == "Test Page Title"
        assert item.raw_html == SAMPLE_HTML
        assert item.canonical_url == "https://example.com/canonical"
