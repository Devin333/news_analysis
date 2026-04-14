"""Smoke tests for the daily report generation path."""

from __future__ import annotations

from datetime import datetime, timezone

from app.agents.report_editor.schemas import (
    ReportEditorOutput,
    ReportSectionOutput,
    ReportType,
)
from app.agents.report_editor.service import ReportEditorService
from app.collectors.base import BaseCollector
from app.collectors.manager import CollectorManager
from app.collectors.registry import CollectorRegistry
from app.common.enums import SourceType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.report import ReportDTO, ReportSectionDTO
from app.contracts.dto.source import CollectRequest, CollectResult, RawCollectedItem, SourceRead
from app.editorial.report_service import ReportService, ReportTopicPayload
from app.processing.pipeline import ProcessingPipeline
from app.scheduler.jobs.collect_job import _raw_collected_to_dto
from scripts.generate_daily_report import generate_daily_reports


class FakeRSSCollector(BaseCollector):
    """Collector that returns a single RSS-like item for smoke tests."""

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
                    url="https://example.com/ai-chip-demand",
                    canonical_url="https://example.com/ai-chip-demand",
                    title="AI chip demand surges",
                    raw_json={
                        "title": "AI chip demand surges",
                        "summary": (
                            "Inference demand is rising across hyperscalers and startups, "
                            "putting pressure on supply chains."
                        ),
                        "author": "NewsAgent",
                        "published": "2026-04-14T08:00:00Z",
                    },
                )
            ],
        )


class ProcessedItemsReportService(ReportService):
    """Report service backed by processed items instead of the database."""

    def __init__(self, items: list[NormalizedItemDTO]) -> None:
        super().__init__()
        self._items = items

    async def select_top_topics_for_report(
        self,
        *,
        window_days: int = 1,
        limit: int = 10,
        use_ranking: bool = True,
    ) -> list[ReportTopicPayload]:
        del window_days, use_ranking

        topics: list[ReportTopicPayload] = []
        for index, item in enumerate(self._items[:limit], start=1):
            topics.append(
                {
                    "id": index,
                    "title": item.title,
                    "summary": item.excerpt or item.clean_text[:200],
                    "board_type": item.board_type_candidate.value,
                    "heat_score": 85.0,
                    "trend_score": 0.72,
                    "item_count": 1,
                    "source_count": 1,
                    "report_score": 1.0 - index / 100,
                }
            )
        return topics


class StubEnhancedDailyReportService:
    """Enhanced report stub for the script-level smoke test."""

    async def generate_daily_report(
        self,
        date: datetime,
        *,
        save_to_db: bool = True,
    ) -> tuple[ReportDTO | None, dict[str, object]]:
        del save_to_db

        return (
            ReportDTO(
                report_type="daily",
                report_date=date,
                title="Enhanced Daily Report",
                executive_summary="Enhanced editorial summary.",
                sections=[
                    ReportSectionDTO(
                        section_id="enhanced",
                        section_title="Enhanced View",
                        section_intro="Agent-written summary.",
                    )
                ],
                topic_count=1,
                generated_at=date,
                status="draft",
            ),
            {"confidence": 0.91},
        )


def _make_source() -> SourceRead:
    return SourceRead(
        id=1,
        name="Test RSS Source",
        source_type=SourceType.RSS,
        base_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        priority=100,
        trust_score=0.8,
        fetch_interval_minutes=60,
        is_active=True,
        metadata_json={},
    )


async def test_collect_process_report_smoke() -> None:
    registry = CollectorRegistry()
    registry.register(FakeRSSCollector())
    manager = CollectorManager(registry)

    collect_results = await manager.collect_many([_make_source()])
    assert len(collect_results) == 1
    assert collect_results[0].success is True
    assert len(collect_results[0].items) == 1

    raw_items = [
        _raw_collected_to_dto(collect_result.source_id, item)
        for collect_result in collect_results
        for item in collect_result.items
    ]

    pipeline_result = ProcessingPipeline().process(raw_items, skip_dedup=True)
    assert pipeline_result.parsed_count == 1
    assert pipeline_result.normalized_count == 1
    assert len(pipeline_result.items) == 1

    result = await generate_daily_reports(
        "2026-04-14",
        report_service=ProcessedItemsReportService(pipeline_result.items),
        editor_service=StubEnhancedDailyReportService(),
    )

    assert result.basic_report is not None
    assert result.basic_report.title == "Daily Tech Intelligence Report - 2026-04-14"
    assert result.basic_report.topic_count == 1
    assert result.basic_report.sections[0].topic_summaries[0].title == "AI chip demand surges"
    assert result.enhanced_report is not None
    assert result.enhanced_metadata["confidence"] == 0.91


def test_report_editor_output_to_dto_smoke() -> None:
    generated_at = datetime(2026, 4, 14, 9, 0, tzinfo=timezone.utc)
    output = ReportEditorOutput(
        report_type=ReportType.DAILY,
        report_title="AI Daily Brief",
        executive_summary="A concise editorial summary of the day.",
        key_highlights=["AI chip demand surges"],
        sections=[
            ReportSectionOutput(
                section_id="top_stories",
                section_title="Top Stories",
                section_intro="The most important developments today.",
                key_points=["Demand accelerated across major cloud vendors."],
                topic_highlights=[
                    {
                        "title": "AI chip demand surges",
                        "summary": "Demand accelerated across major cloud vendors.",
                    }
                ],
                closing_note="Watch supply constraints next.",
            )
        ],
        editorial_conclusion="Capacity planning is now a competitive lever.",
        watch_next_week=["GPU supply chain updates"],
        confidence=0.92,
        generated_at=generated_at,
    )

    dto = ReportEditorService()._output_to_dto(output, generated_at, "daily")

    assert dto.title == "AI Daily Brief"
    assert dto.report_type == "daily"
    assert dto.sections[0].topic_summaries[0].title == "AI chip demand surges"
    assert dto.metadata["confidence"] == 0.92
