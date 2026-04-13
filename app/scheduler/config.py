"""Scheduler configuration and job registration.

This module defines the default job configurations and provides
functions to register all jobs with the scheduler.
"""

from app.bootstrap.logging import get_logger
from app.scheduler.jobs import (
    collect_all_sources_job,
    generate_daily_report_job,
    process_raw_items_job,
    run_daily_workflow,
    trend_hunter_job,
    writer_enrichment_job,
)
from app.scheduler.manager import SchedulerManager
from app.scheduler.models import JobConfig

logger = get_logger(__name__)


# Default job configurations
# Cron expressions use standard format: minute hour day month day_of_week

DEFAULT_JOBS: list[JobConfig] = [
    # Main daily workflow - runs at 6:00 AM every day
    JobConfig(
        job_id="daily_workflow",
        name="Daily Workflow",
        cron_expression="0 6 * * *",  # 6:00 AM daily
        max_retries=3,
        retry_delay_seconds=300,
        enabled=True,
        metadata={"description": "Complete daily workflow: collect, analyze, enrich, report"},
    ),
    
    # Individual jobs for more granular control
    
    # Collection job - runs every 4 hours
    JobConfig(
        job_id="collect_all_sources",
        name="Collect All Sources",
        cron_expression="0 */4 * * *",  # Every 4 hours
        max_retries=3,
        retry_delay_seconds=120,
        enabled=False,  # Disabled by default, use daily_workflow instead
        metadata={"description": "Collect data from all enabled sources"},
    ),
    
    # TrendHunter job - runs twice daily
    JobConfig(
        job_id="trend_hunter",
        name="Trend Hunter",
        cron_expression="0 8,20 * * *",  # 8:00 AM and 8:00 PM
        max_retries=2,
        retry_delay_seconds=180,
        enabled=False,  # Disabled by default
        metadata={"description": "Scan for emerging trends"},
    ),
    
    # Writer enrichment job - runs daily at 7:00 AM
    JobConfig(
        job_id="writer_enrichment",
        name="Writer Enrichment",
        cron_expression="0 7 * * *",  # 7:00 AM daily
        max_retries=2,
        retry_delay_seconds=180,
        enabled=False,  # Disabled by default
        metadata={"description": "Generate content for topics"},
    ),
    
    # Daily report job - runs at 9:00 AM
    JobConfig(
        job_id="generate_daily_report",
        name="Generate Daily Report",
        cron_expression="0 9 * * *",  # 9:00 AM daily
        max_retries=2,
        retry_delay_seconds=300,
        enabled=False,  # Disabled by default
        metadata={"description": "Generate daily summary report"},
    ),
]


# Job function mapping
JOB_FUNCTIONS = {
    "daily_workflow": run_daily_workflow,
    "collect_all_sources": collect_all_sources_job,
    "process_raw_items": process_raw_items_job,
    "trend_hunter": trend_hunter_job,
    "writer_enrichment": writer_enrichment_job,
    "generate_daily_report": generate_daily_report_job,
}


def register_default_jobs(
    scheduler: SchedulerManager,
    *,
    override_configs: dict[str, JobConfig] | None = None,
) -> None:
    """Register all default jobs with the scheduler.
    
    Args:
        scheduler: The scheduler manager instance.
        override_configs: Optional dict of job_id -> JobConfig to override defaults.
    """
    configs = {job.job_id: job for job in DEFAULT_JOBS}
    
    # Apply overrides
    if override_configs:
        for job_id, config in override_configs.items():
            configs[job_id] = config
    
    # Register each job
    for job_id, config in configs.items():
        func = JOB_FUNCTIONS.get(job_id)
        if func is None:
            logger.warning(f"No function found for job {job_id}, skipping")
            continue
        
        scheduler.register_job(config, func)
    
    logger.info(f"Registered {len(configs)} scheduled jobs")


def get_job_config(job_id: str) -> JobConfig | None:
    """Get the default configuration for a job.
    
    Args:
        job_id: The job identifier.
        
    Returns:
        JobConfig or None if not found.
    """
    for job in DEFAULT_JOBS:
        if job.job_id == job_id:
            return job
    return None


def create_custom_config(
    job_id: str,
    *,
    cron_expression: str | None = None,
    interval_seconds: int | None = None,
    enabled: bool | None = None,
    max_retries: int | None = None,
) -> JobConfig | None:
    """Create a custom job config based on defaults.
    
    Args:
        job_id: The job identifier.
        cron_expression: Override cron expression.
        interval_seconds: Override interval (mutually exclusive with cron).
        enabled: Override enabled status.
        max_retries: Override max retries.
        
    Returns:
        New JobConfig with overrides applied, or None if job not found.
    """
    base_config = get_job_config(job_id)
    if base_config is None:
        return None
    
    return JobConfig(
        job_id=base_config.job_id,
        name=base_config.name,
        cron_expression=cron_expression if cron_expression else base_config.cron_expression,
        interval_seconds=interval_seconds if interval_seconds else base_config.interval_seconds,
        max_retries=max_retries if max_retries is not None else base_config.max_retries,
        retry_delay_seconds=base_config.retry_delay_seconds,
        enabled=enabled if enabled is not None else base_config.enabled,
        metadata=base_config.metadata,
    )
