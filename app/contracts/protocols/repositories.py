"""Repository protocol definitions."""

from datetime import datetime
from typing import Protocol

from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.raw_item import RawItemDTO
from app.contracts.dto.report import ReportCreateDTO, ReportDTO
from app.contracts.dto.source import SourceCreate, SourceRead, SourceUpdate
from app.contracts.dto.topic import TopicReadDTO


class SourceRepositoryProtocol(Protocol):
    """Protocol for source repository operations."""

    async def create(self, data: SourceCreate) -> SourceRead:
        """Create a new source."""
        ...

    async def get_by_id(self, source_id: int) -> SourceRead | None:
        """Get source by ID."""
        ...

    async def list_all(self, *, active_only: bool = False) -> list[SourceRead]:
        """List all sources."""
        ...

    async def update(self, source_id: int, data: SourceUpdate) -> SourceRead | None:
        """Update a source."""
        ...

    async def enable(self, source_id: int) -> bool:
        """Enable a source."""
        ...

    async def disable(self, source_id: int) -> bool:
        """Disable a source."""
        ...


class RawItemRepositoryProtocol(Protocol):
    """Protocol for raw item repository operations."""

    async def create(self, data: RawItemDTO) -> RawItemDTO:
        """Create a raw item."""
        ...

    async def bulk_create(self, items: list[RawItemDTO]) -> list[RawItemDTO]:
        """Bulk create raw items."""
        ...

    async def get_by_url(self, url: str) -> RawItemDTO | None:
        """Get raw item by URL."""
        ...

    async def list_by_source(
        self, source_id: int, *, limit: int = 100
    ) -> list[RawItemDTO]:
        """List raw items by source."""
        ...

    async def exists_by_checksum(self, checksum: str) -> bool:
        """Check if item exists by checksum."""
        ...


class NormalizedItemRepositoryProtocol(Protocol):
    """Protocol for normalized item repository operations."""

    async def create(self, data: NormalizedItemDTO) -> NormalizedItemDTO:
        """Create a normalized item."""
        ...

    async def bulk_create(self, items: list[NormalizedItemDTO]) -> list[NormalizedItemDTO]:
        """Bulk create normalized items."""
        ...

    async def get_by_raw_item_id(self, raw_item_id: int) -> NormalizedItemDTO | None:
        """Get normalized item by raw item ID."""
        ...

    async def list_recent(self, *, limit: int = 100) -> list[NormalizedItemDTO]:
        """List recent normalized items."""
        ...

    async def search_candidates(
        self, *, board_type: str | None = None, limit: int = 100
    ) -> list[NormalizedItemDTO]:
        """Search candidate items for topic clustering."""
        ...


class TopicRepositoryProtocol(Protocol):
    """Protocol for topic repository reads used by report generation."""

    async def list_recent(self, *, limit: int = 100) -> list[TopicReadDTO]:
        """List recent topics."""
        ...


class PersistedModelProtocol(Protocol):
    """Protocol for persisted models returned by repositories."""

    id: int


class ReportRepositoryProtocol(Protocol):
    """Protocol for report repository operations."""

    async def create(self, data: ReportCreateDTO) -> PersistedModelProtocol:
        """Create a report."""
        ...

    async def get_by_id(self, report_id: int) -> ReportDTO | None:
        """Get report by ID."""
        ...

    async def get_daily_by_date(self, date: datetime) -> ReportDTO | None:
        """Get a daily report for a given date."""
        ...

    async def get_weekly_by_key(self, week_key: str) -> ReportDTO | None:
        """Get a weekly report by its week key."""
        ...

    async def list_recent(
        self,
        *,
        report_type: str | None = None,
        limit: int = 20,
    ) -> list[ReportDTO]:
        """List recent reports."""
        ...

    async def update_status(
        self,
        report_id: int,
        status: str,
        *,
        review_status: str | None = None,
    ) -> PersistedModelProtocol | None:
        """Update report status."""
        ...
