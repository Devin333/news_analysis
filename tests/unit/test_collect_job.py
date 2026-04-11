"""Unit tests for the wired-up collect job."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.contracts.dto.raw_item import RawItemDTO
from app.contracts.dto.source import SourceRead
from app.scheduler.jobs.collect_job import _raw_collected_to_dto, run_collect_job
from app.scheduler.models import JobRunResult


@pytest.fixture
def mock_source() -> SourceRead:
    return SourceRead(
        id=1,
        name="Test RSS Source",
        source_type="rss",
        base_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        priority=100,
        trust_score=0.5,
        fetch_interval_minutes=60,
        is_active=True,
        metadata_json={},
    )


@pytest.fixture
def mock_raw_collected_item():
    from app.contracts.dto.source import RawCollectedItem

    return RawCollectedItem(
        external_id="test-1",
        url="https://example.com/article1",
        title="Test Article",
        raw_text="Test content",
    )


class TestRawCollectedToDto:
    def test_convert_to_dto(self, mock_raw_collected_item) -> None:
        dto = _raw_collected_to_dto(source_id=1, item=mock_raw_collected_item)
        assert isinstance(dto, RawItemDTO)
        assert dto.source_id == 1
        assert dto.url == "https://example.com/article1"
        assert dto.raw_text == "Test content"
        assert dto.checksum is not None
        assert len(dto.checksum) > 0

    def test_checksum_generation(self, mock_raw_collected_item) -> None:
        dto1 = _raw_collected_to_dto(source_id=1, item=mock_raw_collected_item)
        dto2 = _raw_collected_to_dto(source_id=1, item=mock_raw_collected_item)
        assert dto1.checksum == dto2.checksum


class TestRunCollectJob:
    async def test_source_not_found(self) -> None:
        with patch("app.scheduler.jobs.collect_job.SourceService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.get_source = AsyncMock(return_value=None)
            mock_service_cls.return_value = mock_service

            result = await run_collect_job(source_id=999)

        assert result.success is False
        assert "not found" in result.message

    async def test_no_active_sources(self) -> None:
        with patch("app.scheduler.jobs.collect_job.SourceService") as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.get_source = AsyncMock(return_value=None)
            mock_service.list_sources = AsyncMock(return_value=[])
            mock_service_cls.return_value = mock_service

            result = await run_collect_job(source_id=None)

        assert result.success is True
        assert "No active sources" in result.message
        assert result.items_processed == 0

    async def test_successful_collection(self, mock_source, mock_raw_collected_item) -> None:
        with patch("app.scheduler.jobs.collect_job.SourceService") as mock_service_cls, \
             patch("app.scheduler.jobs.collect_job.CollectorManager") as mock_manager_cls, \
             patch("app.scheduler.jobs.collect_job.UnitOfWork") as mock_uow_cls:

            # Setup source service
            mock_service = AsyncMock()
            mock_service.get_source = AsyncMock(return_value=mock_source)
            mock_service.list_sources = AsyncMock(return_value=[mock_source])
            mock_service_cls.return_value = mock_service

            # Setup collector manager
            from app.contracts.dto.source import CollectResult
            mock_manager = AsyncMock()
            mock_manager.collect_many = AsyncMock(
                return_value=[
                    CollectResult(
                        source_id=1,
                        success=True,
                        items=[mock_raw_collected_item],
                    )
                ]
            )
            mock_manager_cls.return_value = mock_manager

            # Setup UoW
            mock_uow = AsyncMock()
            mock_uow.raw_items.exists_by_checksum = AsyncMock(return_value=False)
            mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
            mock_uow.__aexit__ = AsyncMock(return_value=False)
            mock_uow_cls.return_value = mock_uow

            result = await run_collect_job(source_id=1)

        assert result.success is True
        assert result.items_processed == 1

    async def test_dedup_skips_existing(self, mock_source, mock_raw_collected_item) -> None:
        with patch("app.scheduler.jobs.collect_job.SourceService") as mock_service_cls, \
             patch("app.scheduler.jobs.collect_job.CollectorManager") as mock_manager_cls, \
             patch("app.scheduler.jobs.collect_job.UnitOfWork") as mock_uow_cls:

            # Setup source service
            mock_service = AsyncMock()
            mock_service.get_source = AsyncMock(return_value=mock_source)
            mock_service.list_sources = AsyncMock(return_value=[mock_source])
            mock_service_cls.return_value = mock_service

            # Setup collector manager
            from app.contracts.dto.source import CollectResult
            mock_manager = AsyncMock()
            mock_manager.collect_many = AsyncMock(
                return_value=[
                    CollectResult(
                        source_id=1,
                        success=True,
                        items=[mock_raw_collected_item],
                    )
                ]
            )
            mock_manager_cls.return_value = mock_manager

            # Setup UoW - item already exists
            mock_uow = AsyncMock()
            mock_uow.raw_items.exists_by_checksum = AsyncMock(return_value=True)
            mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
            mock_uow.__aexit__ = AsyncMock(return_value=False)
            mock_uow_cls.return_value = mock_uow

            result = await run_collect_job(source_id=1)

        assert result.success is True
        assert result.items_processed == 0  # Skipped due to dedup
        assert result.metadata.get("items_skipped_dedup") == 1
