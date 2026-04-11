"""Unit tests for the collector framework (base, registry, manager)."""

from app.collectors.base import BaseCollector
from app.collectors.manager import CollectorManager
from app.collectors.registry import CollectorRegistry
from app.common.enums import SourceType
from app.contracts.dto.source import CollectRequest, CollectResult, RawCollectedItem, SourceRead


# ---------------------------------------------------------------------------
# Stub collectors for testing
# ---------------------------------------------------------------------------


class FakeRSSCollector(BaseCollector):
    """Fake RSS collector for testing."""

    @property
    def supported_types(self) -> list[SourceType]:
        return [SourceType.RSS]

    async def collect(self, request: CollectRequest) -> CollectResult:
        return CollectResult(
            source_id=request.source_id,
            success=True,
            items=[
                RawCollectedItem(
                    external_id="rss-1",
                    url="https://example.com/feed/item1",
                    title="Test RSS Item",
                    raw_text="Some content",
                ),
            ],
        )


class FakeWebCollector(BaseCollector):
    """Fake Web collector for testing."""

    @property
    def supported_types(self) -> list[SourceType]:
        return [SourceType.WEB]

    async def collect(self, request: CollectRequest) -> CollectResult:
        return CollectResult(
            source_id=request.source_id,
            success=True,
            items=[
                RawCollectedItem(
                    url="https://example.com/page1",
                    title="Test Web Page",
                    raw_html="<html><body>Hello</body></html>",
                ),
            ],
        )


class FailingCollector(BaseCollector):
    """Collector that always raises an exception."""

    @property
    def supported_types(self) -> list[SourceType]:
        return [SourceType.GITHUB]

    async def collect(self, request: CollectRequest) -> CollectResult:
        raise RuntimeError("Simulated collection failure")


# ---------------------------------------------------------------------------
# Helper to build SourceRead DTOs
# ---------------------------------------------------------------------------


def _make_source(
    source_id: int = 1,
    source_type: SourceType = SourceType.RSS,
    feed_url: str | None = "https://example.com/feed",
) -> SourceRead:
    return SourceRead(
        id=source_id,
        name=f"Test {source_type.value} Source",
        source_type=source_type,
        base_url="https://example.com",
        feed_url=feed_url,
        priority=100,
        trust_score=0.5,
        fetch_interval_minutes=60,
        is_active=True,
        metadata_json={},
    )


# ---------------------------------------------------------------------------
# Tests: BaseCollector
# ---------------------------------------------------------------------------


class TestBaseCollector:
    """Tests for BaseCollector ABC."""

    def test_cannot_instantiate_directly(self) -> None:
        """BaseCollector is abstract and cannot be instantiated."""
        import pytest

        with pytest.raises(TypeError):
            BaseCollector()  # type: ignore[abstract]

    def test_fake_collector_name(self) -> None:
        """Name defaults to class name."""
        collector = FakeRSSCollector()
        assert collector.name == "FakeRSSCollector"

    def test_supported_types(self) -> None:
        """supported_types returns correct list."""
        collector = FakeRSSCollector()
        assert collector.supported_types == [SourceType.RSS]

    async def test_validate_passes_for_matching_type(self) -> None:
        """validate returns None when type matches."""
        collector = FakeRSSCollector()
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.RSS,
            feed_url="https://example.com/feed",
        )
        result = await collector.validate(request)
        assert result is None

    async def test_validate_fails_for_wrong_type(self) -> None:
        """validate returns error message when type does not match."""
        collector = FakeRSSCollector()
        request = CollectRequest(
            source_id=1,
            source_type=SourceType.WEB,
        )
        result = await collector.validate(request)
        assert result is not None
        assert "does not support" in result


# ---------------------------------------------------------------------------
# Tests: CollectorRegistry
# ---------------------------------------------------------------------------


class TestCollectorRegistry:
    """Tests for CollectorRegistry."""

    def test_register_and_get(self) -> None:
        """Register a collector and retrieve it by type."""
        registry = CollectorRegistry()
        collector = FakeRSSCollector()
        registry.register(collector)
        assert registry.get(SourceType.RSS) is collector

    def test_get_unregistered_returns_none(self) -> None:
        """Getting an unregistered type returns None."""
        registry = CollectorRegistry()
        assert registry.get(SourceType.RSS) is None

    def test_has(self) -> None:
        """has() returns True for registered types."""
        registry = CollectorRegistry()
        assert not registry.has(SourceType.RSS)
        registry.register(FakeRSSCollector())
        assert registry.has(SourceType.RSS)

    def test_list_types(self) -> None:
        """list_types returns all registered source types."""
        registry = CollectorRegistry()
        registry.register(FakeRSSCollector())
        registry.register(FakeWebCollector())
        types = registry.list_types()
        assert SourceType.RSS in types
        assert SourceType.WEB in types

    def test_list_collectors(self) -> None:
        """list_collectors returns unique collector instances."""
        registry = CollectorRegistry()
        registry.register(FakeRSSCollector())
        registry.register(FakeWebCollector())
        collectors = registry.list_collectors()
        assert len(collectors) == 2

    def test_register_overwrites(self) -> None:
        """Registering a second collector for the same type overwrites."""
        registry = CollectorRegistry()
        first = FakeRSSCollector()
        second = FakeRSSCollector()
        registry.register(first)
        registry.register(second)
        assert registry.get(SourceType.RSS) is second


# ---------------------------------------------------------------------------
# Tests: CollectorManager
# ---------------------------------------------------------------------------


class TestCollectorManager:
    """Tests for CollectorManager."""

    async def test_collect_source_success(self) -> None:
        """Successful collection returns items."""
        registry = CollectorRegistry()
        registry.register(FakeRSSCollector())
        manager = CollectorManager(registry)

        source = _make_source(source_id=1, source_type=SourceType.RSS)
        result = await manager.collect_source(source)

        assert result.success is True
        assert result.source_id == 1
        assert len(result.items) == 1
        assert result.items[0].title == "Test RSS Item"

    async def test_collect_source_no_collector(self) -> None:
        """Returns error when no collector registered for type."""
        registry = CollectorRegistry()
        manager = CollectorManager(registry)

        source = _make_source(source_type=SourceType.ARXIV)
        result = await manager.collect_source(source)

        assert result.success is False
        assert result.error is not None
        assert "No collector" in result.error

    async def test_collect_source_exception(self) -> None:
        """Returns error when collector raises exception."""
        registry = CollectorRegistry()
        registry.register(FailingCollector())
        manager = CollectorManager(registry)

        source = _make_source(source_id=2, source_type=SourceType.GITHUB)
        result = await manager.collect_source(source)

        assert result.success is False
        assert result.error is not None
        assert "Simulated collection failure" in result.error

    async def test_collect_many(self) -> None:
        """Batch collection returns results for all sources."""
        registry = CollectorRegistry()
        registry.register(FakeRSSCollector())
        registry.register(FakeWebCollector())
        manager = CollectorManager(registry)

        sources = [
            _make_source(source_id=1, source_type=SourceType.RSS),
            _make_source(source_id=2, source_type=SourceType.WEB),
        ]
        results = await manager.collect_many(sources)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is True

    async def test_collect_many_stop_on_error(self) -> None:
        """Batch collection stops on first error when flag is set."""
        registry = CollectorRegistry()
        registry.register(FailingCollector())
        registry.register(FakeRSSCollector())
        manager = CollectorManager(registry)

        sources = [
            _make_source(source_id=1, source_type=SourceType.GITHUB),
            _make_source(source_id=2, source_type=SourceType.RSS),
        ]
        results = await manager.collect_many(sources, stop_on_error=True)

        assert len(results) == 1
        assert results[0].success is False

    def test_supports(self) -> None:
        """supports() checks registry correctly."""
        registry = CollectorRegistry()
        registry.register(FakeRSSCollector())
        manager = CollectorManager(registry)

        assert manager.supports(SourceType.RSS) is True
        assert manager.supports(SourceType.WEB) is False
