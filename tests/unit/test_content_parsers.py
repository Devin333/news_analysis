"""Unit tests for HTML, RSS, and JSON parsers."""

from datetime import datetime, timezone

import pytest

from app.common.enums import ContentType
from app.contracts.dto.raw_item import RawItemDTO
from app.parsers.html import HTMLParser
from app.parsers.json_parser import JSONParser
from app.parsers.rss import RSSParser


# ---------------------------------------------------------------------------
# Sample content
# ---------------------------------------------------------------------------

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Article Title</title>
    <meta name="author" content="John Doe">
    <meta name="keywords" content="python, testing, parser">
    <meta property="article:published_time" content="2026-04-10T12:00:00+00:00">
</head>
<body>
    <h1>Test Article Title</h1>
    <p>This is the first paragraph of the article content.</p>
    <p>This is the second paragraph with more details.</p>
    <img src="https://example.com/image.jpg" alt="Test image">
    <a href="https://example.com/link1">Link 1</a>
    <a href="https://example.com/link2">Link 2</a>
</body>
</html>"""

SAMPLE_RSS_JSON = {
    "id": "entry-123",
    "title": "RSS Entry Title",
    "link": "https://example.com/article",
    "summary": "<p>This is the <strong>summary</strong> of the RSS entry.</p>",
    "author": "Jane Smith",
    "published_parsed": (2026, 4, 10, 14, 30, 0, 0, 0, 0),
    "tags": [{"term": "python"}, {"term": "news"}],
    "enclosures": [
        {"type": "image/jpeg", "href": "https://example.com/thumb.jpg"}
    ],
}

SAMPLE_GITHUB_JSON = {
    "id": 12345,
    "name": "v1.0.0",
    "tag_name": "v1.0.0",
    "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
    "body": "Release notes for version 1.0.0\n\n- Feature A\n- Bug fix B",
    "author": {"login": "developer"},
    "published_at": "2026-04-10T10:00:00Z",
    "stargazers_count": 100,
}

SAMPLE_ARXIV_JSON = {
    "arxiv_id": "2401.12345",
    "title": "A Novel Approach to Machine Learning",
    "abstract": "We present a new method for training neural networks that achieves state-of-the-art results.",
    "authors": ["Alice", "Bob", "Charlie"],
    "published": "2026-04-10T08:00:00Z",
    "primary_category": "cs.LG",
    "categories": ["cs.LG", "cs.AI"],
    "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
}


# ---------------------------------------------------------------------------
# HTMLParser Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def html_parser() -> HTMLParser:
    return HTMLParser()


class TestHTMLParser:
    def test_supported_types(self, html_parser: HTMLParser) -> None:
        assert ContentType.ARTICLE in html_parser.supported_types

    def test_parse_html_success(self, html_parser: HTMLParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1, raw_html=SAMPLE_HTML)
        result = html_parser.parse(raw_item)

        assert result.success is True
        assert result.title == "Test Article Title"
        assert "first paragraph" in result.clean_text
        assert result.author == "John Doe"
        assert result.published_at is not None
        assert result.word_count > 0
        assert len(result.images) > 0
        assert len(result.links) > 0
        assert "python" in result.tags

    def test_parse_plain_text(self, html_parser: HTMLParser) -> None:
        raw_item = RawItemDTO(
            id=1,
            source_id=1,
            raw_text="First line title\n\nThis is the body content.",
        )
        result = html_parser.parse(raw_item)

        assert result.success is True
        assert result.title == "First line title"
        assert "body content" in result.clean_text

    def test_parse_no_content(self, html_parser: HTMLParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1)
        result = html_parser.parse(raw_item)

        assert result.success is False
        assert result.error is not None

    def test_extract_language(self, html_parser: HTMLParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1, raw_html=SAMPLE_HTML)
        result = html_parser.parse(raw_item)

        assert result.language == "en"

    def test_generate_excerpt(self, html_parser: HTMLParser) -> None:
        long_text = "Word " * 100
        excerpt = html_parser._generate_excerpt(long_text, max_length=50)
        assert len(excerpt) <= 53  # 50 + "..."
        assert excerpt.endswith("...")


# ---------------------------------------------------------------------------
# RSSParser Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def rss_parser() -> RSSParser:
    return RSSParser()


class TestRSSParser:
    def test_supported_types(self, rss_parser: RSSParser) -> None:
        # RSSParser now uses THREAD to avoid conflict with HTMLParser
        assert ContentType.THREAD in rss_parser.supported_types

    def test_can_parse_json(self, rss_parser: RSSParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1, raw_json=SAMPLE_RSS_JSON)
        assert rss_parser.can_parse(raw_item) is True

    def test_parse_rss_json(self, rss_parser: RSSParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1, raw_json=SAMPLE_RSS_JSON)
        result = rss_parser.parse(raw_item)

        assert result.success is True
        assert result.title == "RSS Entry Title"
        assert "summary" in result.clean_text
        assert result.author == "Jane Smith"
        assert result.published_at is not None
        assert "python" in result.tags
        assert len(result.images) > 0

    def test_parse_rss_text(self, rss_parser: RSSParser) -> None:
        raw_item = RawItemDTO(
            id=1,
            source_id=1,
            raw_text="RSS Title\n\nRSS content body.",
        )
        result = rss_parser.parse(raw_item)

        assert result.success is True
        assert result.title == "RSS Title"

    def test_strip_html(self, rss_parser: RSSParser) -> None:
        html = "<p>Hello <strong>World</strong></p>"
        clean = rss_parser._strip_html(html)
        assert "<" not in clean
        assert "Hello" in clean
        assert "World" in clean

    def test_extract_date_parsed(self, rss_parser: RSSParser) -> None:
        data = {"published_parsed": (2026, 4, 10, 12, 0, 0, 0, 0, 0)}
        date = rss_parser._extract_date(data)
        assert date is not None
        assert date.year == 2026
        assert date.month == 4


# ---------------------------------------------------------------------------
# JSONParser Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def json_parser() -> JSONParser:
    return JSONParser()


class TestJSONParser:
    def test_supported_types(self, json_parser: JSONParser) -> None:
        assert ContentType.REPOSITORY in json_parser.supported_types
        assert ContentType.PAPER in json_parser.supported_types

    def test_can_parse(self, json_parser: JSONParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1, raw_json={"title": "Test"})
        assert json_parser.can_parse(raw_item) is True

        raw_item_no_json = RawItemDTO(id=1, source_id=1)
        assert json_parser.can_parse(raw_item_no_json) is False

    def test_parse_github(self, json_parser: JSONParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1, raw_json=SAMPLE_GITHUB_JSON)
        result = json_parser.parse(raw_item)

        assert result.success is True
        assert result.title == "v1.0.0"
        assert "Release notes" in result.clean_text
        assert result.author == "developer"
        assert result.published_at is not None
        assert result.metadata.get("stars") == 100

    def test_parse_arxiv(self, json_parser: JSONParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1, raw_json=SAMPLE_ARXIV_JSON)
        result = json_parser.parse(raw_item)

        assert result.success is True
        assert "Novel Approach" in result.title
        assert "neural networks" in result.clean_text
        assert result.author == "Alice"
        assert "cs.LG" in result.tags
        assert result.metadata.get("arxiv_id") == "2401.12345"

    def test_parse_generic(self, json_parser: JSONParser) -> None:
        generic_data = {
            "title": "Generic Title",
            "body": "Generic body content",
            "author": "Generic Author",
            "created_at": "2026-04-10T09:00:00Z",
        }
        raw_item = RawItemDTO(id=1, source_id=1, raw_json=generic_data)
        result = json_parser.parse(raw_item)

        assert result.success is True
        assert result.title == "Generic Title"
        assert result.clean_text == "Generic body content"
        assert result.author == "Generic Author"

    def test_parse_no_json(self, json_parser: JSONParser) -> None:
        raw_item = RawItemDTO(id=1, source_id=1)
        result = json_parser.parse(raw_item)

        assert result.success is False
        assert result.error is not None

    def test_is_github_content(self, json_parser: JSONParser) -> None:
        assert json_parser._is_github_content(SAMPLE_GITHUB_JSON) is True
        assert json_parser._is_github_content(SAMPLE_ARXIV_JSON) is False

    def test_is_arxiv_content(self, json_parser: JSONParser) -> None:
        assert json_parser._is_arxiv_content(SAMPLE_ARXIV_JSON) is True
        assert json_parser._is_arxiv_content(SAMPLE_GITHUB_JSON) is False
