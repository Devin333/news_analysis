"""Collector protocol definitions."""

from typing import Protocol

from app.contracts.dto.source import CollectRequest, CollectResult


class CollectorProtocol(Protocol):
    """Protocol defining the interface all collectors must implement."""

    @property
    def supported_types(self) -> list:  # list[SourceType]
        """Return supported source types."""
        ...

    @property
    def name(self) -> str:
        """Return collector name."""
        ...

    async def collect(self, request: CollectRequest) -> CollectResult:
        """Execute collection."""
        ...

    async def validate(self, request: CollectRequest) -> str | None:
        """Validate request before collection."""
        ...
