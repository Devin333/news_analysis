"""JSON content parser for structured data (GitHub, arXiv, etc.)."""

from datetime import datetime
from typing import Any

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.parsers.base import BaseParser

logger = get_logger(__name__)


class JSONParser(BaseParser):
    """Parser for JSON-structured content like GitHub releases, arXiv papers.

    Handles various JSON formats by looking for common fields:
    - title, name
    - body, description, abstract, summary
    - author, user, owner
    - created_at, published_at, published
    - tags, labels, categories
    """

    READING_SPEED_WPM = 200

    @property
    def supported_types(self) -> list[ContentType]:
        return [ContentType.REPOSITORY, ContentType.PAPER]

    def can_parse(self, raw_item: RawItemDTO) -> bool:
        """Check if raw_json is present."""
        return raw_item.raw_json is not None

    def parse(self, raw_item: RawItemDTO) -> ParseResult:
        """Parse JSON content from raw item."""
        data = raw_item.raw_json
        if not data:
            return ParseResult.failure("No JSON content to parse")

        try:
            # Detect content type and parse accordingly
            if self._is_github_content(data):
                return self._parse_github(data)
            elif self._is_arxiv_content(data):
                return self._parse_arxiv(data)
            else:
                return self._parse_generic(data)

        except Exception as exc:  # noqa: BLE001
            logger.error(f"JSON parsing failed: {exc}")
            return ParseResult.failure(str(exc))

    def _is_github_content(self, data: dict[str, Any]) -> bool:
        """Check if data looks like GitHub API response."""
        return any(
            key in data
            for key in ["html_url", "stargazers_count", "forks_count", "tag_name"]
        )

    def _is_arxiv_content(self, data: dict[str, Any]) -> bool:
        """Check if data looks like arXiv entry."""
        return any(
            key in data
            for key in ["arxiv_id", "primary_category", "pdf_url", "categories"]
        )

    def _parse_github(self, data: dict[str, Any]) -> ParseResult:
        """Parse GitHub-style JSON."""
        # Title: name, full_name, or tag_name
        title = (
            data.get("name")
            or data.get("full_name")
            or data.get("tag_name")
            or ""
        )

        # Content: body or description
        content = data.get("body") or data.get("description") or ""
        clean_text = content.strip()

        # Author
        author = None
        if "author" in data and isinstance(data["author"], dict):
            author = data["author"].get("login")
        elif "user" in data and isinstance(data["user"], dict):
            author = data["user"].get("login")
        elif "owner" in data and isinstance(data["owner"], dict):
            author = data["owner"].get("login")

        # Date
        published_at = self._parse_date(
            data.get("published_at")
            or data.get("created_at")
            or data.get("pushed_at")
        )

        # Tags/labels
        tags: list[str] = []
        if "labels" in data:
            for label in data["labels"]:
                if isinstance(label, dict):
                    tags.append(label.get("name", ""))
                elif isinstance(label, str):
                    tags.append(label)
        if "language" in data and data["language"]:
            tags.append(data["language"])

        # Links
        links: list[str] = []
        if "html_url" in data:
            links.append(data["html_url"])

        # Metrics
        word_count = len(clean_text.split())
        reading_time = max(1, word_count // self.READING_SPEED_WPM)

        return ParseResult(
            success=True,
            title=title,
            clean_text=clean_text,
            excerpt=self._generate_excerpt(clean_text),
            author=author,
            published_at=published_at,
            tags=[t for t in tags if t],
            links=links,
            word_count=word_count,
            reading_time_minutes=reading_time,
            metadata={
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "type": data.get("type", "github"),
            },
        )

    def _parse_arxiv(self, data: dict[str, Any]) -> ParseResult:
        """Parse arXiv-style JSON."""
        title = data.get("title", "")
        abstract = data.get("abstract") or data.get("summary") or ""
        clean_text = abstract.strip()

        # Authors
        authors = data.get("authors", [])
        author = authors[0] if authors else None

        # Date
        published_at = self._parse_date(
            data.get("published") or data.get("published_at")
        )

        # Categories as tags
        tags = data.get("categories", [])
        if data.get("primary_category"):
            tags = [data["primary_category"]] + [t for t in tags if t != data["primary_category"]]

        # Links
        links: list[str] = []
        if "pdf_url" in data:
            links.append(data["pdf_url"])
        if "url" in data:
            links.append(data["url"])

        # Metrics
        word_count = len(clean_text.split())
        reading_time = max(1, word_count // self.READING_SPEED_WPM)

        return ParseResult(
            success=True,
            title=title,
            clean_text=clean_text,
            excerpt=self._generate_excerpt(clean_text),
            author=author,
            published_at=published_at,
            tags=tags[:10],
            links=links,
            word_count=word_count,
            reading_time_minutes=reading_time,
            metadata={
                "arxiv_id": data.get("arxiv_id"),
                "doi": data.get("doi"),
                "comment": data.get("comment"),
                "type": "paper",
            },
        )

    def _parse_generic(self, data: dict[str, Any]) -> ParseResult:
        """Parse generic JSON structure."""
        # Title
        title = (
            data.get("title")
            or data.get("name")
            or data.get("headline")
            or ""
        )

        # Content
        content = (
            data.get("body")
            or data.get("content")
            or data.get("description")
            or data.get("text")
            or data.get("summary")
            or ""
        )
        clean_text = str(content).strip()

        # Author
        author = data.get("author") or data.get("creator")
        if isinstance(author, dict):
            author = author.get("name") or author.get("login")

        # Date
        published_at = self._parse_date(
            data.get("published_at")
            or data.get("created_at")
            or data.get("date")
            or data.get("timestamp")
        )

        # Tags
        tags = data.get("tags") or data.get("keywords") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        # Metrics
        word_count = len(clean_text.split())
        reading_time = max(1, word_count // self.READING_SPEED_WPM)

        return ParseResult(
            success=True,
            title=title,
            clean_text=clean_text,
            excerpt=self._generate_excerpt(clean_text),
            author=author,
            published_at=published_at,
            tags=tags[:10] if isinstance(tags, list) else [],
            word_count=word_count,
            reading_time_minutes=reading_time,
        )

    def _parse_date(self, date_value: Any) -> datetime | None:
        """Parse date from various formats."""
        if date_value is None:
            return None

        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except ValueError:
                pass

        return None

    def _generate_excerpt(self, text: str, max_length: int = 200) -> str:
        """Generate excerpt from text."""
        if len(text) <= max_length:
            return text

        excerpt = text[:max_length]
        last_space = excerpt.rfind(" ")
        if last_space > max_length // 2:
            excerpt = excerpt[:last_space]

        return excerpt.rstrip(".,;:") + "..."
