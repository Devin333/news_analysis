"""Base parser abstract class."""

from abc import ABC, abstractmethod

from app.common.enums import ContentType
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO


class BaseParser(ABC):
    """Abstract base class for all content parsers.

    Each concrete parser must:
    - Declare which ContentType(s) it handles via `supported_types`.
    - Implement `parse()` to extract structured content from raw items.
    """

    @property
    @abstractmethod
    def supported_types(self) -> list[ContentType]:
        """Return the list of ContentType values this parser can handle."""
        ...

    @property
    def name(self) -> str:
        """Human-readable parser name (defaults to class name)."""
        return self.__class__.__name__

    @abstractmethod
    def parse(self, raw_item: RawItemDTO) -> ParseResult:
        """Parse a raw item and extract structured content.

        Args:
            raw_item: RawItemDTO containing raw_html, raw_text, or raw_json.

        Returns:
            ParseResult with extracted content or error details.
        """
        ...

    def can_parse(self, raw_item: RawItemDTO) -> bool:
        """Check if this parser can handle the given raw item.

        Default implementation checks if raw_html or raw_text is present.
        Override for more specific checks.
        """
        return bool(raw_item.raw_html or raw_item.raw_text or raw_item.raw_json)
