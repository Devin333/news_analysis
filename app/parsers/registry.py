"""Parser registry for mapping ContentType to parser instances."""

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.parsers.base import BaseParser

logger = get_logger(__name__)


class ParserRegistry:
    """Registry that maps ContentType to parser instances.

    Usage:
        registry = ParserRegistry()
        registry.register(HTMLParser())
        parser = registry.get(ContentType.ARTICLE)
    """

    def __init__(self) -> None:
        self._parsers: dict[ContentType, BaseParser] = {}
        self._default_parser: BaseParser | None = None

    def register(self, parser: BaseParser, *, as_default: bool = False) -> None:
        """Register a parser for its supported types.

        Args:
            parser: A BaseParser instance.
            as_default: If True, use this parser as fallback for unknown types.
        """
        for content_type in parser.supported_types:
            if content_type in self._parsers:
                logger.warning(
                    f"Overwriting parser for {content_type}: "
                    f"{self._parsers[content_type].name} -> {parser.name}"
                )
            self._parsers[content_type] = parser
            logger.info(f"Registered parser {parser.name} for {content_type}")

        if as_default:
            self._default_parser = parser
            logger.info(f"Set {parser.name} as default parser")

    def get(self, content_type: ContentType) -> BaseParser | None:
        """Get the parser for a given content type.

        Args:
            content_type: The ContentType to look up.

        Returns:
            The registered parser, default parser, or None if not found.
        """
        return self._parsers.get(content_type) or self._default_parser

    def has(self, content_type: ContentType) -> bool:
        """Check if a parser is registered for the given type."""
        return content_type in self._parsers or self._default_parser is not None

    def list_types(self) -> list[ContentType]:
        """Return all registered content types."""
        return list(self._parsers.keys())

    def list_parsers(self) -> list[BaseParser]:
        """Return all unique registered parsers."""
        seen: set[int] = set()
        result: list[BaseParser] = []
        for parser in self._parsers.values():
            if id(parser) not in seen:
                seen.add(id(parser))
                result.append(parser)
        if self._default_parser and id(self._default_parser) not in seen:
            result.append(self._default_parser)
        return result


# Global default registry instance
_default_registry: ParserRegistry | None = None


def get_parser_registry() -> ParserRegistry:
    """Get or create the default global parser registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ParserRegistry()
    return _default_registry


def register_parser(parser: BaseParser, *, as_default: bool = False) -> None:
    """Convenience function to register a parser in the default registry."""
    get_parser_registry().register(parser, as_default=as_default)
