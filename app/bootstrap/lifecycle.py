"""Application lifecycle management."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.bootstrap.logging import get_logger, setup_logging
from app.bootstrap.settings import get_settings
from app.collectors.setup import setup_collectors
from app.common.exceptions import InfrastructureError
from app.scheduler.manager import scheduler_manager
from app.storage.db.session import ping_database

logger = get_logger(__name__)


def _setup_scheduled_jobs() -> None:
    """Setup scheduled jobs based on settings."""
    from app.scheduler.config import create_custom_config, register_default_jobs
    from app.scheduler.models import JobConfig
    
    settings = get_settings()
    sched_settings = settings.scheduler
    
    # Build override configs based on settings
    override_configs: dict[str, JobConfig] = {}
    
    # Daily workflow
    if sched_settings.daily_workflow_enabled:
        config = create_custom_config(
            "daily_workflow",
            cron_expression=sched_settings.daily_workflow_cron,
            enabled=True,
        )
        if config:
            override_configs["daily_workflow"] = config
    
    # Collection job
    if sched_settings.collection_enabled:
        config = create_custom_config(
            "collect_all_sources",
            cron_expression=sched_settings.collection_cron,
            enabled=True,
        )
        if config:
            override_configs["collect_all_sources"] = config
    
    # TrendHunter job
    if sched_settings.trend_hunter_enabled:
        config = create_custom_config(
            "trend_hunter",
            cron_expression=sched_settings.trend_hunter_cron,
            enabled=True,
        )
        if config:
            override_configs["trend_hunter"] = config
    
    # Writer enrichment job
    if sched_settings.writer_enrichment_enabled:
        config = create_custom_config(
            "writer_enrichment",
            cron_expression=sched_settings.writer_enrichment_cron,
            enabled=True,
        )
        if config:
            override_configs["writer_enrichment"] = config
    
    # Daily report job
    if sched_settings.daily_report_enabled:
        config = create_custom_config(
            "generate_daily_report",
            cron_expression=sched_settings.daily_report_cron,
            enabled=True,
        )
        if config:
            override_configs["generate_daily_report"] = config
    
    # Register all jobs with the global scheduler_manager
    register_default_jobs(scheduler_manager, override_configs=override_configs)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    settings = get_settings()

    # Startup
    setup_logging(debug=settings.app.debug)
    logger.info(
        "Application starting",
        extra={
            "app_name": settings.app.name,
            "environment": settings.app.env,
        },
    )

    # Setup collectors
    setup_collectors()

    # Database connectivity check
    try:
        await ping_database()
        logger.info("Database connection established")
    except InfrastructureError as exc:
        logger.warning(f"Database not available: {exc.message}")

    # Start scheduler (optional - can be disabled via env)
    if settings.app.env != "testing" and settings.scheduler.enabled:
        # Setup scheduled jobs
        _setup_scheduled_jobs()
        
        # Start the scheduler
        scheduler_manager.start()
        logger.info("Scheduler started with scheduled jobs")

    yield

    # Shutdown
    if scheduler_manager.is_running:
        scheduler_manager.stop()
        logger.info("Scheduler stopped")
    logger.info("Application shutting down")
