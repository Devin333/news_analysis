"""arXiv Collector using arXiv API."""

import hashlib
import re
import time
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

import httpx

from app.bootstrap.logging import get_logger
from app.collectors.base import BaseCollector
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest, CollectResult, RawCollectedItem

logger = get_logger(__name__)


class ArxivCollector(BaseCollector):
    """Collector for arXiv papers via the arXiv API.

    Supports searching by:
    - Category (e.g., cs.AI, cs.LG)
    - Keywords
    - Author
    """

    API_BASE = "http://export.arxiv.org/api/query"
    DEFAULT_TIMEOUT = 60.0  # arXiv can be slow

    # XML namespaces
    ATOM_NS = "{http://www.w3.org/2005/Atom}"
    ARXIV_NS = "{http://arxiv.org/schemas/atom}"

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize ArxivCollector.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self._timeout = timeout

    @property
    def supported_types(self) -> list[SourceType]:
        return [SourceType.ARXIV]

    async def validate(self, request: CollectRequest) -> str | None:
        """Validate request has search criteria."""
        base_error = await super().validate(request)
        if base_error:
            return base_error

        # Need either base_url (category) or metadata with search query
        if not request.base_url and not request.metadata_json.get("query"):
            return "arXiv collector requires base_url (category) or metadata.query"
        return None

    async def collect(self, request: CollectRequest) -> CollectResult:
        """Fetch arXiv papers based on request configuration."""
        start = time.monotonic()

        # Build search query
        query = self._build_query(request)
        if not query:
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error="No valid search query",
                duration_seconds=time.monotonic() - start,
            )

        logger.info(f"Searching arXiv: {query}")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    self.API_BASE,
                    params={
                        "search_query": query,
                        "start": 0,
                        "max_results": request.max_items,
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                    },
                )
                response.raise_for_status()

            items = self._parse_response(response.text, request.source_id)

            return CollectResult(
                source_id=request.source_id,
                success=True,
                items=items,
                duration_seconds=time.monotonic() - start,
                metadata={"query": query, "result_count": len(items)},
            )

        except httpx.HTTPStatusError as exc:
            logger.error(f"arXiv API error: {exc.response.status_code}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=f"arXiv API error: {exc.response.status_code}",
                duration_seconds=time.monotonic() - start,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"arXiv collection failed: {exc}")
            return CollectResult(
                source_id=request.source_id,
                success=False,
                error=str(exc),
                duration_seconds=time.monotonic() - start,
            )

    def _build_query(self, request: CollectRequest) -> str:
        """Build arXiv search query from request."""
        parts: list[str] = []

        # Category from base_url
        if request.base_url:
            category = request.base_url.strip("/")
            parts.append(f"cat:{category}")

        # Additional query from metadata
        meta = request.metadata_json
        if meta.get("query"):
            parts.append(meta["query"])
        if meta.get("author"):
            parts.append(f"au:{meta['author']}")
        if meta.get("title"):
            parts.append(f"ti:{meta['title']}")

        return " AND ".join(parts) if parts else ""

    def _parse_response(self, xml_text: str, source_id: int) -> list[RawCollectedItem]:
        """Parse arXiv Atom XML response."""
        items: list[RawCollectedItem] = []

        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            logger.error(f"Failed to parse arXiv XML: {exc}")
            return items

        for entry in root.findall(f"{self.ATOM_NS}entry"):
            item = self._entry_to_item(entry, source_id)
            if item:
                items.append(item)

        return items

    def _entry_to_item(
        self, entry: ElementTree.Element, source_id: int
    ) -> RawCollectedItem | None:
        """Convert arXiv entry to RawCollectedItem."""
        # ID (arXiv identifier)
        id_elem = entry.find(f"{self.ATOM_NS}id")
        if id_elem is None or not id_elem.text:
            return None

        arxiv_url = id_elem.text
        arxiv_id = self._extract_arxiv_id(arxiv_url)

        # Title
        title_elem = entry.find(f"{self.ATOM_NS}title")
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

        # Abstract/Summary
        summary_elem = entry.find(f"{self.ATOM_NS}summary")
        abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""

        # Authors
        authors: list[str] = []
        for author_elem in entry.findall(f"{self.ATOM_NS}author"):
            name_elem = author_elem.find(f"{self.ATOM_NS}name")
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text)

        # Published date
        published_elem = entry.find(f"{self.ATOM_NS}published")
        published_at = None
        if published_elem is not None and published_elem.text:
            published_at = self._parse_date(published_elem.text)

        # Updated date
        updated_elem = entry.find(f"{self.ATOM_NS}updated")
        updated_at = None
        if updated_elem is not None and updated_elem.text:
            updated_at = self._parse_date(updated_elem.text)

        # Categories
        categories: list[str] = []
        for cat_elem in entry.findall(f"{self.ATOM_NS}category"):
            term = cat_elem.get("term")
            if term:
                categories.append(term)

        # PDF link
        pdf_url = None
        for link_elem in entry.findall(f"{self.ATOM_NS}link"):
            if link_elem.get("title") == "pdf":
                pdf_url = link_elem.get("href")
                break

        # Comment (version info, pages, etc.)
        comment_elem = entry.find(f"{self.ARXIV_NS}comment")
        comment = comment_elem.text if comment_elem is not None and comment_elem.text else None

        # DOI
        doi_elem = entry.find(f"{self.ARXIV_NS}doi")
        doi = doi_elem.text if doi_elem is not None and doi_elem.text else None

        return RawCollectedItem(
            external_id=arxiv_id,
            url=arxiv_url,
            canonical_url=f"https://arxiv.org/abs/{arxiv_id}",
            title=title,
            raw_text=abstract,
            published_at=published_at,
            author=authors[0] if authors else None,
            extra={
                "authors": authors,
                "categories": categories,
                "primary_category": categories[0] if categories else None,
                "pdf_url": pdf_url,
                "updated_at": updated_at.isoformat() if updated_at else None,
                "comment": comment,
                "doi": doi,
                "type": "paper",
            },
        )

    @staticmethod
    def _extract_arxiv_id(url: str) -> str:
        """Extract arXiv ID from URL."""
        # URL format: http://arxiv.org/abs/2401.12345v1
        match = re.search(r"arxiv\.org/abs/(.+?)(?:v\d+)?$", url)
        if match:
            return match.group(1)
        # Fallback: use last path segment
        return url.rstrip("/").split("/")[-1]

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        """Parse ISO date string."""
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return None
