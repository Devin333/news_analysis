#!/usr/bin/env python
"""Generate daily report script.

Usage:
    python scripts/generate_daily_report.py [--date YYYY-MM-DD]
"""

import argparse
import asyncio
from datetime import datetime, timezone


async def main(date_str: str | None = None) -> None:
    """Generate a daily report.

    Args:
        date_str: Optional date string (YYYY-MM-DD).
    """
    from app.agents.report_editor.service import ReportEditorService
    from app.editorial.report_service import ReportService

    # Parse date
    if date_str:
        report_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        report_date = datetime.now(timezone.utc)

    print(f"Generating daily report for {report_date.date()}...")

    # Use ReportService for basic report
    report_service = ReportService()
    report = await report_service.build_daily_report(report_date)

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

    # Optionally use ReportEditorAgent for enhanced report
    print("\n--- Using ReportEditorAgent ---")
    editor_service = ReportEditorService()
    enhanced_report, meta = await editor_service.generate_daily_report(
        report_date,
        save_to_db=False,
    )

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
