#!/usr/bin/env python
"""Generate weekly report script.

Usage:
    python scripts/generate_weekly_report.py [--week-key YYYY-WNN]
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone


async def main(week_key: str | None = None) -> None:
    """Generate a weekly report.

    Args:
        week_key: Optional week key (YYYY-WNN).
    """
    from app.agents.report_editor.service import ReportEditorService
    from app.editorial.report_service import ReportService

    # Calculate dates
    now = datetime.now(timezone.utc)
    if week_key:
        # Parse week key
        year, week = week_key.split("-W")
        # Get first day of that week
        start_date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").replace(tzinfo=timezone.utc)
    else:
        # Default to current week
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        week_key = start_date.strftime("%Y-W%W")

    end_date = start_date + timedelta(days=6)

    print(f"Generating weekly report for {week_key}...")
    print(f"Period: {start_date.date()} to {end_date.date()}")

    # Use ReportService for basic report
    report_service = ReportService()
    report = await report_service.build_weekly_report(start_date, end_date)

    if report:
        print(f"\n=== Weekly Report ===")
        print(f"Title: {report.title}")
        print(f"Week: {week_key}")
        print(f"Topics: {report.topic_count}")
        print(f"\nExecutive Summary:")
        print(report.executive_summary)
        print(f"\nSections: {len(report.sections)}")
        for section in report.sections:
            print(f"  - {section.section_title} ({len(section.topic_summaries)} topics)")
    else:
        print("Failed to generate report")

    # Optionally use ReportEditorAgent for enhanced report
    print("\n--- Using ReportEditorAgent ---")
    editor_service = ReportEditorService()
    enhanced_report, meta = await editor_service.generate_weekly_report(
        start_date,
        end_date,
        save_to_db=False,
    )

    if enhanced_report:
        print(f"Enhanced report generated with confidence: {meta.get('confidence', 'N/A')}")
    else:
        print("ReportEditorAgent did not generate output (LLM not configured)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate weekly report")
    parser.add_argument(
        "--week-key",
        type=str,
        help="Week key (YYYY-WNN, e.g., 2026-W15)",
        default=None,
    )
    args = parser.parse_args()

    asyncio.run(main(args.week_key))
