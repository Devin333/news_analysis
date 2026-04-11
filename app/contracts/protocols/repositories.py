"""Repository protocol definitions."""

from typing import Protocol

from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.raw_item import RawItemDTO
from app.contracts.dto.source import SourceCreate, SourceRead, SourceUpdate


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
