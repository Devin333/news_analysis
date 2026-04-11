"""HTML content parser using BeautifulSoup and optional trafilatura."""

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.parsers.base import BaseParser

logger = get_logger(__name__)

# Optional trafilatura for better content extraction
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    trafilatura = None  # type: ignore[assignment]
    HAS_TRAFILATURA = False


class HTMLParser(BaseParser):
    """Parser for HTML content using BeautifulSoup.

    Extracts:
    - Title from <title> or <h1>
    - Clean text content
    - Author from meta tags
    - Published date from meta tags
    - Images and links
    """

    # Average reading speed (words per minute)
    READING_SPEED_WPM = 200

    @property
    def supported_types(self) -> list[ContentType]:
        return [ContentType.ARTICLE, ContentType.THREAD]

    def parse(self, raw_item: RawItemDTO) -> ParseResult:
        """Parse HTML content from raw item."""
        html = raw_item.raw_html
        if not html:
            # Fallback to raw_text if no HTML
            if raw_item.raw_text:
                return self._parse_plain_text(raw_item.raw_text)
            return ParseResult.failure("No HTML or text content to parse")

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title = self._extract_title(soup)

            # Extract clean text
            clean_text = self._extract_text(html, soup)

            # Extract metadata
            author = self._extract_author(soup)
            published_at = self._extract_date(soup)
            language = self._extract_language(soup)

            # Extract media
            images = self._extract_images(soup)
            links = self._extract_links(soup)
            tags = self._extract_tags(soup)

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
                language=language,
                tags=tags,
                images=images,
                links=links,
                word_count=word_count,
                reading_time_minutes=reading_time,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(f"HTML parsing failed: {exc}")
            return ParseResult.failure(str(exc))

    def _parse_plain_text(self, text: str) -> ParseResult:
        """Parse plain text content."""
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

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML."""
        # Try <title> tag
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        # Try <h1>
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Try og:title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]

        return ""

    def _extract_text(self, html: str, soup: BeautifulSoup) -> str:
        """Extract clean text from HTML."""
        # Try trafilatura first for better extraction
        if HAS_TRAFILATURA:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )
            if extracted:
                return extracted

        # Fallback to BeautifulSoup
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        return text.strip()

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        """Extract author from meta tags."""
        # Try meta author
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"]

        # Try article:author
        article_author = soup.find("meta", property="article:author")
        if article_author and article_author.get("content"):
            return article_author["content"]

        # Try schema.org author
        author_elem = soup.find(itemprop="author")
        if author_elem:
            name_elem = author_elem.find(itemprop="name")
            if name_elem:
                return name_elem.get_text(strip=True)
            return author_elem.get_text(strip=True)

        return None

    def _extract_date(self, soup: BeautifulSoup) -> datetime | None:
        """Extract published date from meta tags."""
        date_metas = [
            ("property", "article:published_time"),
            ("name", "pubdate"),
            ("name", "publishdate"),
            ("name", "date"),
            ("itemprop", "datePublished"),
        ]

        for attr, value in date_metas:
            tag = soup.find("meta", attrs={attr: value})
            if tag and tag.get("content"):
                try:
                    return datetime.fromisoformat(
                        tag["content"].replace("Z", "+00:00")
                    )
                except ValueError:
                    continue

        # Try time element
        time_elem = soup.find("time", datetime=True)
        if time_elem:
            try:
                return datetime.fromisoformat(
                    time_elem["datetime"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        return None

    def _extract_language(self, soup: BeautifulSoup) -> str | None:
        """Extract language from HTML."""
        # Try html lang attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return html_tag["lang"][:2].lower()

        # Try meta language
        meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta_lang and meta_lang.get("content"):
            return meta_lang["content"][:2].lower()

        return None

    def _extract_images(self, soup: BeautifulSoup) -> list[str]:
        """Extract image URLs from HTML."""
        images: list[str] = []

        # Get og:image first
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            images.append(og_image["content"])

        # Get img tags
        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src and src not in images:
                images.append(src)

        return images[:10]  # Limit to 10 images

    def _extract_links(self, soup: BeautifulSoup) -> list[str]:
        """Extract links from HTML."""
        links: list[str] = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href and href.startswith("http") and href not in links:
                links.append(href)

        return links[:20]  # Limit to 20 links

    def _extract_tags(self, soup: BeautifulSoup) -> list[str]:
        """Extract tags/keywords from HTML."""
        tags: list[str] = []

        # Try meta keywords
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and meta_keywords.get("content"):
            keywords = meta_keywords["content"].split(",")
            tags.extend(k.strip() for k in keywords if k.strip())

        # Try article:tag
        for tag_meta in soup.find_all("meta", property="article:tag"):
            if tag_meta.get("content"):
                tags.append(tag_meta["content"])

        return list(set(tags))[:10]  # Dedupe and limit

    def _generate_excerpt(self, text: str, max_length: int = 200) -> str:
        """Generate excerpt from text."""
        if len(text) <= max_length:
            return text

        # Find a good break point
        excerpt = text[:max_length]
        last_space = excerpt.rfind(" ")
        if last_space > max_length // 2:
            excerpt = excerpt[:last_space]

        return excerpt.rstrip(".,;:") + "..."
