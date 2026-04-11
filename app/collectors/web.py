"""Web page collector using httpx and trafilatura."""

import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.bootstrap.logging import get_logger
from app.collectors.base import BaseCollector
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest, CollectResult, RawCollectedItem

logger = get_logger(__name__)

# Optional trafilatura import for content extraction
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    trafilatura = None  # type: ignore[assignment]
    HAS_TRAFILATURA = False


class WebPageCollector(BaseCollector):
    """Collector for web pages using httpx and optional trafilatura extraction."""

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (compatible; NewsAgent/1.0; +https://github.com/newsagent)"
    )

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        follow_links: bool = False,
        max_depth: int = 1,
    ) -> None:
        """Initialize WebPageCollector.

        Args:
            timeout: HTTP request timeout in seconds.
            user_agent: User-Agent header for requests.
            follow_links: Whether to follow links on the page.
            max_depth: Maximum link depth to follow (if follow_links=True).
        """
        self._timeout = timeout
        self._user_agent = user_agent
        self._follow_links = follow_links
        self._max_depth = max_depth

    @property
    def supported_types(self) -> list[SourceType]:
        return [SourceType.WEB]

    async def validate(self, request: CollectRequest) -> str | None:
        """Validate that base_url is provided."""
        base_error = await super().validate(request)
        if base_error:
            return base_error
        if not request.base_url:
            return "Web collector requires base_url"
        return None

    async def collect(self, request: CollectRequest) -> CollectResult:
        """Fetch web page(s) and extract content."""
        start = time.monotonic()
        base_url = request.base_url

        if not base_url:
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error="base_url is required",
                duration_seconds=time.monotonic() - start,
            )

        logger.info(f"Fetching web page: {base_url}")

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": self._user_agent},
                follow_redirects=True,
            ) as client:
                items = await self._fetch_page(client, base_url, request)

                if self._follow_links and len(items) < request.max_items:
                    # Optionally follow links from the main page
                    items = await self._follow_page_links(
                        client, base_url, items, request
                    )

            items = items[: request.max_items]

            return CollectResult(
                source_id=request.source_id,
                success=True,
                items=items,
                duration_seconds=time.monotonic() - start,
                metadata={
                    "base_url": base_url,
                    "items_collected": len(items),
                    "follow_links": self._follow_links,
                },
            )

        except httpx.TimeoutException as exc:
            logger.error(f"Timeout fetching {base_url}: {exc}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=f"Request timeout: {exc}",
                duration_seconds=time.monotonic() - start,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error for {base_url}: {exc.response.status_code}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=f"HTTP {exc.response.status_code}",
                duration_seconds=time.monotonic() - start,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Web collection failed for {base_url}: {exc}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=str(exc),
                duration_seconds=time.monotonic() - start,
            )

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        request: CollectRequest,
    ) -> list[RawCollectedItem]:
        """Fetch a single page and convert to RawCollectedItem."""
        response = await client.get(url)
        response.raise_for_status()

        html = response.text
        item = self._html_to_item(url, html, request.source_id)
        return [item] if item else []

    async def _follow_page_links(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        existing_items: list[RawCollectedItem],
        request: CollectRequest,
    ) -> list[RawCollectedItem]:
        """Extract and follow links from the main page."""
        if not existing_items:
            return existing_items

        main_item = existing_items[0]
        if not main_item.raw_html:
            return existing_items

        links = self._extract_links(main_item.raw_html, base_url)
        seen_urls = {item.url for item in existing_items}
        items = list(existing_items)

        for link in links:
            if link in seen_urls:
                continue
            if len(items) >= request.max_items:
                break

            try:
                response = await client.get(link)
                response.raise_for_status()
                item = self._html_to_item(link, response.text, request.source_id)
                if item:
                    items.append(item)
                    seen_urls.add(link)
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Failed to fetch link {link}: {exc}")
                continue

        return items

    def _html_to_item(
        self, url: str, html: str, source_id: int
    ) -> RawCollectedItem | None:
        """Convert HTML to RawCollectedItem with optional trafilatura extraction."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Extract text content
        raw_text = None
        if HAS_TRAFILATURA:
            extracted = trafilatura.extract(html, include_comments=False)
            if extracted:
                raw_text = extracted

        # Extract metadata
        extra: dict[str, Any] = {}
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            extra["description"] = meta_desc["content"]

        meta_author = soup.find("meta", attrs={"name": "author"})
        author = None
        if meta_author and meta_author.get("content"):
            author = meta_author["content"]

        # Canonical URL
        canonical_url = url
        canonical_link = soup.find("link", attrs={"rel": "canonical"})
        if canonical_link and canonical_link.get("href"):
            canonical_url = canonical_link["href"]

        # Published date from meta tags
        published_at = self._extract_publish_date(soup)

        return RawCollectedItem(
            external_id=self._hash_url(url),
            url=url,
            canonical_url=canonical_url,
            title=title,
            raw_html=html,
            raw_text=raw_text,
            published_at=published_at,
            author=author,
            extra=extra,
        )

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract article-like links from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(base_url).netloc
        links: list[str] = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Only same-domain links
            if parsed.netloc != base_domain:
                continue

            # Skip common non-article patterns
            path = parsed.path.lower()
            if any(
                skip in path
                for skip in [
                    "/tag/",
                    "/category/",
                    "/author/",
                    "/page/",
                    "/search",
                    "/login",
                    "/register",
                    "/contact",
                    "/about",
                    "#",
                ]
            ):
                continue

            # Prefer paths that look like articles
            if full_url not in links:
                links.append(full_url)

        return links[:50]  # Limit to avoid too many requests

    def _extract_publish_date(self, soup: BeautifulSoup) -> datetime | None:
        """Try to extract publish date from common meta tags."""
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

        return None

    @staticmethod
    def _hash_url(url: str) -> str:
        """Generate a short hash for URL as external_id."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
