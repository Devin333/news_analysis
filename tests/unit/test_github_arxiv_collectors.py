"""Unit tests for GitHubCollector and ArxivCollector."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.arxiv import ArxivCollector
from app.collectors.github import GitHubCollector
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest


# ---------------------------------------------------------------------------
# Sample API responses
# ---------------------------------------------------------------------------

SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.12345v1</id>
    <title>Test Paper Title</title>
    <summary>This is the abstract of the test paper.</summary>
    <author><name>John Doe</name></author>
    <author><name>Jane Smith</name></author>
    <published>2026-04-10T12:00:00Z</published>
    <updated>2026-04-10T14:00:00Z</updated>
    <category term="cs.AI" />
    <category term="cs.LG" />
    <link title="pdf" href="http://arxiv.org/pdf/2401.12345v1" />
    <arxiv:comment>10 pages, 5 figures</arxiv:comment>
    <arxiv:doi>10.1234/example</arxiv:doi>
  </entry>
</feed>"""

SAMPLE_GITHUB_RELEASES = [
    {
        "id": 12345,
        "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
        "tag_name": "v1.0.0",
        "name": "Version 1.0.0",
        "body": "Release notes for v1.0.0",
        "published_at": "2026-04-10T12:00:00Z",
        "author": {"login": "developer"},
    }
]

SAMPLE_GITHUB_ISSUES = [
    {
        "id": 67890,
        "html_url": "https://github.com/owner/repo/issues/1",
        "title": "Bug report",
        "body": "Description of the bug",
        "number": 1,
        "state": "open",
        "created_at": "2026-04-10T10:00:00Z",
        "user": {"login": "reporter"},
        "labels": [{"name": "bug"}],
    }
]


# ---------------------------------------------------------------------------
# ArxivCollector Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def arxiv_collector() -> ArxivCollector:
    return ArxivCollector(timeout=10.0)


@pytest.fixture
def arxiv_request() -> CollectRequest:
    return CollectRequest(
        source_id=1,
        source_type=SourceType.ARXIV,
        base_url="cs.AI",
        max_items=10,
    )


class TestArxivCollectorProperties:
    def test_supported_types(self, arxiv_collector: ArxivCollector) -> None:
        assert arxiv_collector.supported_types == [SourceType.ARXIV]

    def test_name(self, arxiv_collector: ArxivCollector) -> None:
        assert arxiv_collector.name == "ArxivCollector"


class TestArxivCollectorValidation:
    async def test_validate_success(
        self, arxiv_collector: ArxivCollector, arxiv_request: CollectRequest
    ) -> None:
        result = await arxiv_collector.validate(arxiv_request)
        assert result is None

    async def test_validate_with_query(self, arxiv_collector: ArxivCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.ARXIV,
            metadata_json={"query": "machine learning"},
        )
        result = await arxiv_collector.validate(request)
        assert result is None

    async def test_validate_missing_criteria(self, arxiv_collector: ArxivCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.ARXIV,
        )
        result = await arxiv_collector.validate(request)
        assert result is not None
        assert "requires" in result


class TestArxivCollectorCollect:
    async def test_collect_success(
        self, arxiv_collector: ArxivCollector, arxiv_request: CollectRequest
    ) -> None:
        mock_response = MagicMock()
        mock_response.text = SAMPLE_ARXIV_XML
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.arxiv.httpx.AsyncClient", return_value=mock_client):
            result = await arxiv_collector.collect(arxiv_request)

        assert result.success is True
        assert len(result.items) == 1
        item = result.items[0]
        assert item.external_id == "2401.12345"
        assert item.title == "Test Paper Title"
        assert item.author == "John Doe"
        assert item.extra["authors"] == ["John Doe", "Jane Smith"]
        assert "cs.AI" in item.extra["categories"]

    async def test_collect_no_query(self, arxiv_collector: ArxivCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.ARXIV,
        )
        result = await arxiv_collector.collect(request)
        assert result.success is False
        assert result.error is not None


class TestArxivCollectorHelpers:
    def test_extract_arxiv_id(self) -> None:
        url = "http://arxiv.org/abs/2401.12345v1"
        assert ArxivCollector._extract_arxiv_id(url) == "2401.12345"

    def test_build_query_category(self, arxiv_collector: ArxivCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.ARXIV,
            base_url="cs.AI",
        )
        query = arxiv_collector._build_query(request)
        assert "cat:cs.AI" in query

    def test_build_query_with_author(self, arxiv_collector: ArxivCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.ARXIV,
            base_url="cs.AI",
            metadata_json={"author": "Hinton"},
        )
        query = arxiv_collector._build_query(request)
        assert "au:Hinton" in query


# ---------------------------------------------------------------------------
# GitHubCollector Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def github_collector() -> GitHubCollector:
    return GitHubCollector(timeout=10.0)


@pytest.fixture
def github_request() -> CollectRequest:
    return CollectRequest(
        source_id=1,
        source_type=SourceType.GITHUB,
        base_url="owner/repo",
        max_items=10,
        metadata_json={"mode": "releases"},
    )


class TestGitHubCollectorProperties:
    def test_supported_types(self, github_collector: GitHubCollector) -> None:
        assert github_collector.supported_types == [SourceType.GITHUB]

    def test_name(self, github_collector: GitHubCollector) -> None:
        assert github_collector.name == "GitHubCollector"


class TestGitHubCollectorValidation:
    async def test_validate_success(
        self, github_collector: GitHubCollector, github_request: CollectRequest
    ) -> None:
        result = await github_collector.validate(github_request)
        assert result is None

    async def test_validate_missing_base_url(self, github_collector: GitHubCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.GITHUB,
        )
        result = await github_collector.validate(request)
        assert result is not None
        assert "base_url" in result


class TestGitHubCollectorCollect:
    async def test_collect_releases(
        self, github_collector: GitHubCollector, github_request: CollectRequest
    ) -> None:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=SAMPLE_GITHUB_RELEASES)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.github.httpx.AsyncClient", return_value=mock_client):
            result = await github_collector.collect(github_request)

        assert result.success is True
        assert len(result.items) == 1
        item = result.items[0]
        assert item.title == "Version 1.0.0"
        assert item.extra["tag"] == "v1.0.0"
        assert item.extra["type"] == "release"

    async def test_collect_issues(self, github_collector: GitHubCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.GITHUB,
            base_url="owner/repo",
            metadata_json={"mode": "issues"},
        )

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=SAMPLE_GITHUB_ISSUES)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.collectors.github.httpx.AsyncClient", return_value=mock_client):
            result = await github_collector.collect(request)

        assert result.success is True
        assert len(result.items) == 1
        item = result.items[0]
        assert item.title == "Bug report"
        assert item.extra["type"] == "issue"
        assert "bug" in item.extra["labels"]

    async def test_collect_missing_base_url(self, github_collector: GitHubCollector) -> None:
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.GITHUB,
        )
        result = await github_collector.collect(request)
        assert result.success is False
        assert result.error is not None


class TestGitHubCollectorHelpers:
    def test_build_headers_without_token(self, github_collector: GitHubCollector) -> None:
        headers = github_collector._build_headers()
        assert "Authorization" not in headers
        assert "Accept" in headers

    def test_build_headers_with_token(self) -> None:
        collector = GitHubCollector(token="test_token")
        headers = collector._build_headers()
        assert "Authorization" in headers
        assert "Bearer test_token" in headers["Authorization"]
