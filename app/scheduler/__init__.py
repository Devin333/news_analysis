"""Scheduler module for scheduled job execution.

This module provides:
- SchedulerManager: APScheduler wrapper for job management
- JobConfig, JobRunResult: Data models for jobs
- Job functions: Predefined jobs for agent execution
- Configuration: Default job configs and registration
"""

from app.scheduler.config import (
    DEFAULT_JOBS,
    JOB_FUNCTIONS,
    create_custom_config,
    get_job_config,
    register_default_jobs,
)
from app.scheduler.jobs import (
    collect_all_sources_job,
    generate_daily_report_job,
    process_raw_items_job,
    run_collect_job,
    run_daily_workflow,
    trend_hunter_job,
    writer_enrichment_job,
)
from app.scheduler.manager import SchedulerManager, scheduler_manager
from app.scheduler.models import JobConfig, JobRunResult, RetryPolicy

__all__ = [
    # Manager
    "SchedulerManager",
    "scheduler_manager",
    # Models
    "JobConfig",
    "JobRunResult",
    "RetryPolicy",
    # Jobs
    "collect_all_sources_job",
    "generate_daily_report_job",
    "process_raw_items_job",
    "run_collect_job",
    "run_daily_workflow",
    "trend_hunter_job",
    "writer_enrichment_job",
    # Config
    "DEFAULT_JOBS",
    "JOB_FUNCTIONS",
    "create_custom_config",
    "get_job_config",
    "register_default_jobs",
]
