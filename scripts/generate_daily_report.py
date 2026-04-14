#!/usr/bin/env python
"""Generate daily report script.

Usage:
    python scripts/generate_daily_report.py [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Mapping, Protocol

if TYPE_CHECKING:
    from app.contracts.dto.report import ReportDTO


class BasicDailyReportService(Protocol):
    """Protocol for the basic daily report builder."""

    async def build_daily_report(self, date: datetime) -> "ReportDTO | None":
        """Build the basic daily report for the requested date."""
        ...


class EnhancedDailyReportService(Protocol):
    """Protocol for the enhanced daily report builder."""

    async def generate_daily_report(
        self,
        date: datetime,
        *,
        save_to_db: bool = True,
    ) -> tuple["ReportDTO | None", Mapping[str, object]]:
        """Generate the enhanced daily report for the requested date."""
        ...


@dataclass(slots=True)
class DailyReportGenerationResult:
    """Typed result for daily report generation."""

    report_date: datetime
    basic_report: "ReportDTO | None"
    enhanced_report: "ReportDTO | None"
    enhanced_metadata: dict[str, object]


def parse_report_date(date_str: str | None) -> datetime:
    """Parse a CLI date string into a UTC datetime."""

    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _build_default_services() -> tuple[BasicDailyReportService, EnhancedDailyReportService]:
    from app.agents.report_editor.service import ReportEditorService
    from app.editorial.report_service import ReportService

    return ReportService(), ReportEditorService()


async def generate_daily_reports(
    date_str: str | None = None,
    *,
    report_service: BasicDailyReportService | None = None,
    editor_service: EnhancedDailyReportService | None = None,
) -> DailyReportGenerationResult:
    """Generate both the basic and enhanced daily report variants."""

    resolved_report_service = report_service
    resolved_editor_service = editor_service
    if resolved_report_service is None or resolved_editor_service is None:
        default_report_service, default_editor_service = _build_default_services()
        resolved_report_service = resolved_report_service or default_report_service
        resolved_editor_service = resolved_editor_service or default_editor_service

    report_date = parse_report_date(date_str)
    basic_report = await resolved_report_service.build_daily_report(report_date)
    enhanced_report, meta = await resolved_editor_service.generate_daily_report(
        report_date,
        save_to_db=False,
    )

    return DailyReportGenerationResult(
        report_date=report_date,
        basic_report=basic_report,
        enhanced_report=enhanced_report,
        enhanced_metadata=dict(meta),
    )


async def main(date_str: str | None = None) -> None:
    """Generate a daily report.

    Args:
        date_str: Optional date string (YYYY-MM-DD).
    """
    result = await generate_daily_reports(date_str)
    report_date = result.report_date

    print(f"Generating daily report for {report_date.date()}...")

    report = result.basic_report

    if report:
        print(f"\n=== Daily Report ===")
        print(f"Title: {report.title}")
        print(f"Date: {report.report_date}")
        print(f"Topics: {report.topic_count}")
        print(f"\nExecutive Summary:")
        print(report.executive_summary)
        print(f"\nSections: {len(report.sections)}")
        for section in report.sections:
            print(f"  - {section.section_title}")
    else:
        print("Failed to generate report")

    print("\n--- Using ReportEditorAgent ---")
    enhanced_report = result.enhanced_report
    meta = result.enhanced_metadata

    if enhanced_report:
        print(f"Enhanced report generated with confidence: {meta.get('confidence', 'N/A')}")
    else:
        print("ReportEditorAgent did not generate output (LLM not configured)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily report")
    parser.add_argument(
        "--date",
        type=str,
        help="Report date (YYYY-MM-DD)",
        default=None,
    )
    args = parser.parse_args()

    asyncio.run(main(args.date))
