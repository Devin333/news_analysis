"""Scheduler jobs module.

Exports all job functions for scheduling.
"""

from app.scheduler.jobs.agent_workflow_job import (
    generate_daily_report_job,
    process_raw_items_job,
    run_daily_workflow,
    trend_hunter_job,
    writer_enrichment_job,
)
from app.scheduler.jobs.collect_job import run_collect_job

# Alias for consistency
collect_all_sources_job = run_collect_job

__all__ = [
    "collect_all_sources_job",
    "generate_daily_report_job",
    "process_raw_items_job",
    "run_collect_job",
    "run_daily_workflow",
    "trend_hunter_job",
    "writer_enrichment_job",
]
