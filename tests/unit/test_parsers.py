"""Unit tests for the parser framework (base, registry, manager)."""

import pytest

from app.common.enums import ContentType
from app.contracts.dto.parse_result import ParseResult
from app.contracts.dto.raw_item import RawItemDTO
from app.parsers.base import BaseParser
from app.parsers.manager import ParserManager
from app.parsers.registry import ParserRegistry


# ---------------------------------------------------------------------------
# Stub parsers for testing
# ---------------------------------------------------------------------------


class FakeArticleParser(BaseParser):
    """Fake parser for articles."""

    @property
    def supported_types(self) -> list[ContentType]:
        return [ContentType.ARTICLE]

    def parse(self, raw_item: RawItemDTO) -> ParseResult:
        text = raw_item.raw_text or raw_item.raw_html or ""
        return ParseResult(
            success=True,
            title="Parsed Title",
            clean_text=text[:100],
            word_count=len(text.split()),
        )


class FakeVideoParser(BaseParser):
    """Fake parser for video content."""

    @property
    def supported_types(self) -> list[ContentType]:
        return [ContentType.VIDEO]

    def parse(self, raw_item: RawItemDTO) -> ParseResult:
        return ParseResult(
            success=True,
            title="Video Title",
            clean_text="Video description",
            metadata={"duration": 120},
        )


class FailingParser(BaseParser):
    """Parser that always raises an exception."""

    @property
    def supported_types(self) -> list[ContentType]:
        return [ContentType.PAPER]

    def parse(self, raw_item: RawItemDTO) -> ParseResult:
        raise RuntimeError("Simulated parse failure")


# ---------------------------------------------------------------------------
# Helper to build RawItemDTO
# ---------------------------------------------------------------------------


def _make_raw_item(
    item_id: int = 1,
    raw_text: str | None = "Sample text content for parsing",
    raw_html: str | None = None,
) -> RawItemDTO:
    return RawItemDTO(
        id=item_id,
        source_id=1,
        raw_text=raw_text,
        raw_html=raw_html,
    )


# ---------------------------------------------------------------------------
# Tests: BaseParser
# ---------------------------------------------------------------------------


class TestBaseParser:
    """Tests for BaseParser ABC."""

    def test_cannot_instantiate_directly(self) -> None:
        """BaseParser is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseParser()  # type: ignore[abstract]

    def test_fake_parser_name(self) -> None:
        """Name defaults to class name."""
        parser = FakeArticleParser()
        assert parser.name == "FakeArticleParser"

    def test_supported_types(self) -> None:
        """supported_types returns correct list."""
        parser = FakeArticleParser()
        assert parser.supported_types == [ContentType.ARTICLE]

    def test_can_parse_with_text(self) -> None:
        """can_parse returns True when raw_text is present."""
        parser = FakeArticleParser()
        raw_item = _make_raw_item(raw_text="Some text")
        assert parser.can_parse(raw_item) is True

    def test_can_parse_with_html(self) -> None:
        """can_parse returns True when raw_html is present."""
        parser = FakeArticleParser()
        raw_item = _make_raw_item(raw_text=None, raw_html="<p>HTML</p>")
        assert parser.can_parse(raw_item) is True

    def test_can_parse_empty(self) -> None:
        """can_parse returns False when no content."""
        parser = FakeArticleParser()
        raw_item = _make_raw_item(raw_text=None, raw_html=None)
        assert parser.can_parse(raw_item) is False


# ---------------------------------------------------------------------------
# Tests: ParserRegistry
# ---------------------------------------------------------------------------


class TestParserRegistry:
    """Tests for ParserRegistry."""

    def test_register_and_get(self) -> None:
        """Register a parser and retrieve it by type."""
        registry = ParserRegistry()
        parser = FakeArticleParser()
        registry.register(parser)
        assert registry.get(ContentType.ARTICLE) is parser

    def test_get_unregistered_returns_none(self) -> None:
        """Getting an unregistered type returns None."""
        registry = ParserRegistry()
        assert registry.get(ContentType.ARTICLE) is None

    def test_default_parser(self) -> None:
        """Default parser is used for unregistered types."""
        registry = ParserRegistry()
        default = FakeArticleParser()
        registry.register(default, as_default=True)
        assert registry.get(ContentType.VIDEO) is default

    def test_has(self) -> None:
        """has() returns True for registered types."""
        registry = ParserRegistry()
        assert not registry.has(ContentType.ARTICLE)
        registry.register(FakeArticleParser())
        assert registry.has(ContentType.ARTICLE)

    def test_list_types(self) -> None:
        """list_types returns all registered content types."""
        registry = ParserRegistry()
        registry.register(FakeArticleParser())
        registry.register(FakeVideoParser())
        types = registry.list_types()
        assert ContentType.ARTICLE in types
        assert ContentType.VIDEO in types

    def test_list_parsers(self) -> None:
        """list_parsers returns unique parser instances."""
        registry = ParserRegistry()
        registry.register(FakeArticleParser())
        registry.register(FakeVideoParser())
        parsers = registry.list_parsers()
        assert len(parsers) == 2

    def test_register_overwrites(self) -> None:
        """Registering a second parser for the same type overwrites."""
        registry = ParserRegistry()
        first = FakeArticleParser()
        second = FakeArticleParser()
        registry.register(first)
        registry.register(second)
        assert registry.get(ContentType.ARTICLE) is second


# ---------------------------------------------------------------------------
# Tests: ParserManager
# ---------------------------------------------------------------------------


class TestParserManager:
    """Tests for ParserManager."""

    def test_parse_item_success(self) -> None:
        """Successful parsing returns ParseResult."""
        registry = ParserRegistry()
        registry.register(FakeArticleParser())
        manager = ParserManager(registry)

        raw_item = _make_raw_item()
        result = manager.parse_item(raw_item, ContentType.ARTICLE)

        assert result.success is True
        assert result.title == "Parsed Title"
        assert result.word_count > 0

    def test_parse_item_no_parser(self) -> None:
        """Returns error when no parser registered for type."""
        registry = ParserRegistry()
        manager = ParserManager(registry)

        raw_item = _make_raw_item()
        result = manager.parse_item(raw_item, ContentType.PAPER)

        assert result.success is False
        assert result.error is not None
        assert "No parser" in result.error

    def test_parse_item_cannot_parse(self) -> None:
        """Returns error when parser cannot handle item."""
        registry = ParserRegistry()
        registry.register(FakeArticleParser())
        manager = ParserManager(registry)

        raw_item = _make_raw_item(raw_text=None, raw_html=None)
        result = manager.parse_item(raw_item, ContentType.ARTICLE)

        assert result.success is False
        assert result.error is not None
        assert "cannot handle" in result.error

    def test_parse_item_exception(self) -> None:
        """Returns error when parser raises exception."""
        registry = ParserRegistry()
        registry.register(FailingParser())
        manager = ParserManager(registry)

        raw_item = _make_raw_item()
        result = manager.parse_item(raw_item, ContentType.PAPER)

        assert result.success is False
        assert result.error is not None
        assert "Simulated parse failure" in result.error

    def test_parse_many(self) -> None:
        """Batch parsing returns results for all items."""
        registry = ParserRegistry()
        registry.register(FakeArticleParser())
        manager = ParserManager(registry)

        raw_items = [
            _make_raw_item(item_id=1),
            _make_raw_item(item_id=2),
            _make_raw_item(item_id=3),
        ]
        job_result = manager.parse_many(raw_items, ContentType.ARTICLE)

        assert job_result.total == 3
        assert job_result.success_count == 3
        assert job_result.failure_count == 0
        assert len(job_result.results) == 3

    def test_parse_many_with_failures(self) -> None:
        """Batch parsing handles mixed success/failure."""
        registry = ParserRegistry()
        registry.register(FailingParser())
        manager = ParserManager(registry)

        raw_items = [
            _make_raw_item(item_id=1),
            _make_raw_item(item_id=2),
        ]
        job_result = manager.parse_many(raw_items, ContentType.PAPER)

        assert job_result.total == 2
        assert job_result.failure_count == 2
        assert len(job_result.errors) == 2

    def test_parse_many_stop_on_error(self) -> None:
        """Batch parsing stops on first error when flag is set."""
        registry = ParserRegistry()
        registry.register(FailingParser())
        manager = ParserManager(registry)

        raw_items = [
            _make_raw_item(item_id=1),
            _make_raw_item(item_id=2),
            _make_raw_item(item_id=3),
        ]
        job_result = manager.parse_many(raw_items, ContentType.PAPER, stop_on_error=True)

        assert job_result.total == 3
        assert len(job_result.results) == 1  # Stopped after first

    def test_supports(self) -> None:
        """supports() checks registry correctly."""
        registry = ParserRegistry()
        registry.register(FakeArticleParser())
        manager = ParserManager(registry)

        assert manager.supports(ContentType.ARTICLE) is True
        assert manager.supports(ContentType.VIDEO) is False
