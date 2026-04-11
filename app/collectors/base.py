"""Base collector abstract class."""

from abc import ABC, abstractmethod

from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest, CollectResult


class BaseCollector(ABC):
    """Abstract base class for all collectors.

    Each concrete collector must:
    - Declare which SourceType(s) it handles via `supported_types`.
    - Implement `collect()` to fetch raw items from the source.
    """

    @property
    @abstractmethod
    def supported_types(self) -> list[SourceType]:
        """Return the list of SourceType values this collector can handle."""
        ...

    @property
    def name(self) -> str:
        """Human-readable collector name (defaults to class name)."""
        return self.__class__.__name__

    @abstractmethod
    async def collect(self, request: CollectRequest) -> CollectResult:
        """Execute collection for the given request.

        Args:
            request: CollectRequest containing source info and limits.

        Returns:
            CollectResult with collected items or error details.
        """
        ...

    async def validate(self, request: CollectRequest) -> str | None:
        """Optional pre-flight validation.

        Returns:
            None if valid, or an error message string.
        """
        if request.source_type not in self.supported_types:
            return f"Collector {self.name} does not support {request.source_type}"
        return None
