"""Scheduler manager wrapping APScheduler."""

from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.bootstrap.logging import get_logger
from app.scheduler.models import JobConfig

logger = get_logger(__name__)


class SchedulerManager:
    """Manage scheduled jobs using APScheduler."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._jobs: dict[str, JobConfig] = {}

    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def register_job(
        self,
        config: JobConfig,
        func: Callable[..., Any],
        **kwargs: Any,
    ) -> None:
        """Register a job with the scheduler."""
        if not config.enabled:
            logger.info(f"Job {config.job_id} is disabled, skipping registration")
            return

        trigger = None
        if config.cron_expression:
            trigger = CronTrigger.from_crontab(config.cron_expression)
        elif config.interval_seconds:
            trigger = IntervalTrigger(seconds=config.interval_seconds)
        else:
            logger.warning(f"Job {config.job_id} has no trigger configured")
            return

        self._scheduler.add_job(
            func,
            trigger=trigger,
            id=config.job_id,
            name=config.name,
            replace_existing=True,
            kwargs=kwargs,
        )
        self._jobs[config.job_id] = config
        logger.info(f"Registered job: {config.job_id} ({config.name})")

    def unregister_job(self, job_id: str) -> bool:
        """Remove a job from the scheduler."""
        if job_id in self._jobs:
            self._scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"Unregistered job: {job_id}")
            return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        if job_id in self._jobs:
            self._scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if job_id in self._jobs:
            self._scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        return False

    def get_jobs(self) -> list[JobConfig]:
        """Get all registered job configs."""
        return list(self._jobs.values())

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._scheduler.running


# Global scheduler instance
scheduler_manager = SchedulerManager()
