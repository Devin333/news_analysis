"""RSS/Atom feed entry parser."""

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.parsers.base import BaseParser

logger = get_logger(__name__)

# Optional BeautifulSoup for HTML stripping
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None  # type: ignore[misc, assignment]
    HAS_BS4 = False


class RSSParser(BaseParser):
    """Parser for RSS/Atom feed entries stored as raw_json.

    Expects raw_json to contain feedparser-style entry data:
    - title
    - summary or content
    - author
    - published/updated
    - tags
    - links
    """

    READING_SPEED_WPM = 200

    @property
    def supported_types(self) -> list[ContentType]:
        # RSS parser handles THREAD type to avoid conflict with HTMLParser
        # It's used when raw_json contains RSS entry data
        return [ContentType.THREAD]

    def can_parse(self, raw_item: RawItemDTO) -> bool:
        """Check if raw_json contains RSS entry data."""
        if raw_item.raw_json:
            return True
        # Also accept raw_text for simple RSS text content
        return bool(raw_item.raw_text)

    def parse(self, raw_item: RawItemDTO) -> ParseResult:
        """Parse RSS entry from raw_json or raw_text."""
        if raw_item.raw_json:
            return self._parse_json_entry(raw_item.raw_json)
        elif raw_item.raw_text:
            return self._parse_text_entry(raw_item.raw_text)
        else:
            return ParseResult.failure("No JSON or text content to parse")

    def _parse_json_entry(self, data: dict[str, Any]) -> ParseResult:
        """Parse RSS entry from JSON data."""
        try:
            # Extract title
            title = data.get("title", "")

            # Extract content
            content = self._extract_content(data)
            clean_text = self._strip_html(content)

            # Extract author
            author = self._extract_author(data)

            # Extract date
            published_at = self._extract_date(data)

            # Extract tags
            tags = self._extract_tags(data)

            # Extract links
            links = self._extract_links(data)

            # Extract images from enclosures
            images = self._extract_images(data)

            # Calculate metrics
            word_count = len(clean_text.split())
            reading_time = max(1, word_count // self.READING_SPEED_WPM)

            # Generate excerpt
            excerpt = self._generate_excerpt(clean_text)

            return ParseResult(
                success=True,
                title=title,
                clean_text=clean_text,
                excerpt=excerpt,
                author=author,
                published_at=published_at,
                tags=tags,
                images=images,
                links=links,
                word_count=word_count,
                reading_time_minutes=reading_time,
                metadata={
                    "feed_id": data.get("id"),
                    "feed_link": data.get("link"),
                },
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(f"RSS parsing failed: {exc}")
            return ParseResult.failure(str(exc))

    def _parse_text_entry(self, text: str) -> ParseResult:
        """Parse plain text RSS content."""
        clean_text = text.strip()
        word_count = len(clean_text.split())
        reading_time = max(1, word_count // self.READING_SPEED_WPM)

        # Try to extract title from first line
        lines = clean_text.split("\n")
        title = lines[0][:100] if lines else ""

        return ParseResult(
            success=True,
            title=title,
            clean_text=clean_text,
            excerpt=self._generate_excerpt(clean_text),
            word_count=word_count,
            reading_time_minutes=reading_time,
        )

    def _extract_content(self, data: dict[str, Any]) -> str:
        """Extract content from RSS entry."""
        # Try content array first (Atom style)
        if "content" in data and data["content"]:
            content_items = data["content"]
            if isinstance(content_items, list) and content_items:
                return content_items[0].get("value", "")
            elif isinstance(content_items, str):
                return content_items

        # Try summary
        if "summary" in data:
            return data["summary"]

        # Try description
        if "description" in data:
            return data["description"]

        return ""

    def _extract_author(self, data: dict[str, Any]) -> str | None:
        """Extract author from RSS entry."""
        if "author" in data:
            return data["author"]

        if "author_detail" in data:
            detail = data["author_detail"]
            if isinstance(detail, dict):
                return detail.get("name")

        if "authors" in data and data["authors"]:
            first_author = data["authors"][0]
            if isinstance(first_author, dict):
                return first_author.get("name")
            return str(first_author)

        return None

    def _extract_date(self, data: dict[str, Any]) -> datetime | None:
        """Extract published date from RSS entry."""
        # Try parsed struct first
        for key in ("published_parsed", "updated_parsed"):
            parsed = data.get(key)
            if parsed:
                try:
                    return datetime(*parsed[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    pass

        # Try raw string
        for key in ("published", "updated", "pubDate"):
            raw = data.get(key)
            if raw:
                try:
                    return parsedate_to_datetime(raw)
                except (TypeError, ValueError):
                    pass
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    pass

        return None

    def _extract_tags(self, data: dict[str, Any]) -> list[str]:
        """Extract tags from RSS entry."""
        tags: list[str] = []

        if "tags" in data:
            for tag in data["tags"]:
                if isinstance(tag, dict):
                    term = tag.get("term")
                    if term:
                        tags.append(term)
                elif isinstance(tag, str):
                    tags.append(tag)

        if "categories" in data:
            for cat in data["categories"]:
                if isinstance(cat, str) and cat not in tags:
                    tags.append(cat)

        return tags[:10]

    def _extract_links(self, data: dict[str, Any]) -> list[str]:
        """Extract links from RSS entry."""
        links: list[str] = []

        # Main link
        if "link" in data and data["link"]:
            links.append(data["link"])

        # Additional links
        if "links" in data:
            for link in data["links"]:
                if isinstance(link, dict):
                    href = link.get("href")
                    if href and href not in links:
                        links.append(href)
                elif isinstance(link, str) and link not in links:
                    links.append(link)

        return links[:10]

    def _extract_images(self, data: dict[str, Any]) -> list[str]:
        """Extract images from RSS enclosures."""
        images: list[str] = []

        if "enclosures" in data:
            for enc in data["enclosures"]:
                if isinstance(enc, dict):
                    enc_type = enc.get("type", "")
                    if enc_type.startswith("image/"):
                        url = enc.get("href") or enc.get("url")
                        if url:
                            images.append(url)

        # Try media_content
        if "media_content" in data:
            for media in data["media_content"]:
                if isinstance(media, dict):
                    medium = media.get("medium", "")
                    if medium == "image" or media.get("type", "").startswith("image/"):
                        url = media.get("url")
                        if url:
                            images.append(url)

        return images[:5]

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""

        if HAS_BS4:
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text(separator=" ", strip=True)

        # Fallback: simple regex
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()

    def _generate_excerpt(self, text: str, max_length: int = 200) -> str:
        """Generate excerpt from text."""
        if len(text) <= max_length:
            return text

        excerpt = text[:max_length]
        last_space = excerpt.rfind(" ")
        if last_space > max_length // 2:
            excerpt = excerpt[:last_space]

        return excerpt.rstrip(".,;:") + "..."
