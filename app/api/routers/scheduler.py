"""Scheduler management API endpoints."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.bootstrap.logging import get_logger
from app.scheduler.config import JOB_FUNCTIONS, get_job_config
from app.scheduler.manager import scheduler_manager
from app.scheduler.models import JobRunResult

logger = get_logger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class JobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    name: str
    enabled: bool
    cron_expression: str | None
    interval_seconds: int | None
    next_run_time: str | None


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""

    running: bool
    job_count: int
    jobs: list[JobStatusResponse]


class TriggerJobResponse(BaseModel):
    """Response model for manual job trigger."""

    job_id: str
    status: str
    message: str


class JobResultResponse(BaseModel):
    """Response model for job execution result."""

    job_id: str
    success: bool
    message: str
    items_processed: int
    duration_seconds: float
    error: str | None
    metadata: dict[str, Any]


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status() -> SchedulerStatusResponse:
    """Get the current scheduler status and registered jobs."""
    jobs = scheduler_manager.get_jobs()
    
    job_statuses = []
    for job_config in jobs:
        # Try to get next run time from APScheduler
        next_run = None
        try:
            ap_job = scheduler_manager._scheduler.get_job(job_config.job_id)
            if ap_job and ap_job.next_run_time:
                next_run = ap_job.next_run_time.isoformat()
        except Exception:
            pass
        
        job_statuses.append(
            JobStatusResponse(
                job_id=job_config.job_id,
                name=job_config.name,
                enabled=job_config.enabled,
                cron_expression=job_config.cron_expression,
                interval_seconds=job_config.interval_seconds,
                next_run_time=next_run,
            )
        )
    
    return SchedulerStatusResponse(
        running=scheduler_manager.is_running,
        job_count=len(jobs),
        jobs=job_statuses,
    )


@router.get("/jobs", response_model=list[JobStatusResponse])
async def list_jobs() -> list[JobStatusResponse]:
    """List all registered jobs."""
    jobs = scheduler_manager.get_jobs()
    
    result = []
    for job_config in jobs:
        next_run = None
        try:
            ap_job = scheduler_manager._scheduler.get_job(job_config.job_id)
            if ap_job and ap_job.next_run_time:
                next_run = ap_job.next_run_time.isoformat()
        except Exception:
            pass
        
        result.append(
            JobStatusResponse(
                job_id=job_config.job_id,
                name=job_config.name,
                enabled=job_config.enabled,
                cron_expression=job_config.cron_expression,
                interval_seconds=job_config.interval_seconds,
                next_run_time=next_run,
            )
        )
    
    return result


@router.post("/jobs/{job_id}/trigger", response_model=TriggerJobResponse)
async def trigger_job(
    job_id: str,
    background_tasks: BackgroundTasks,
) -> TriggerJobResponse:
    """Manually trigger a job to run immediately.
    
    The job runs in the background and this endpoint returns immediately.
    """
    # Check if job exists
    job_func = JOB_FUNCTIONS.get(job_id)
    if job_func is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Add to background tasks
    background_tasks.add_task(job_func)
    
    logger.info(f"Manually triggered job: {job_id}")
    
    return TriggerJobResponse(
        job_id=job_id,
        status="triggered",
        message=f"Job {job_id} has been triggered and is running in the background",
    )


@router.post("/jobs/{job_id}/run", response_model=JobResultResponse)
async def run_job_sync(job_id: str) -> JobResultResponse:
    """Run a job synchronously and wait for the result.
    
    Warning: This may take a long time depending on the job.
    """
    # Check if job exists
    job_func = JOB_FUNCTIONS.get(job_id)
    if job_func is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    logger.info(f"Running job synchronously: {job_id}")
    
    try:
        result: JobRunResult = await job_func()
        
        return JobResultResponse(
            job_id=result.job_id,
            success=result.success,
            message=result.message,
            items_processed=result.items_processed,
            duration_seconds=result.duration_seconds,
            error=result.error,
            metadata=result.metadata,
        )
    except Exception as exc:
        logger.error(f"Job {job_id} failed with exception: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/jobs/{job_id}/pause", response_model=TriggerJobResponse)
async def pause_job(job_id: str) -> TriggerJobResponse:
    """Pause a scheduled job."""
    success = scheduler_manager.pause_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or not registered")
    
    return TriggerJobResponse(
        job_id=job_id,
        status="paused",
        message=f"Job {job_id} has been paused",
    )


@router.post("/jobs/{job_id}/resume", response_model=TriggerJobResponse)
async def resume_job(job_id: str) -> TriggerJobResponse:
    """Resume a paused job."""
    success = scheduler_manager.resume_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or not registered")
    
    return TriggerJobResponse(
        job_id=job_id,
        status="resumed",
        message=f"Job {job_id} has been resumed",
    )


@router.get("/available-jobs")
async def list_available_jobs() -> list[dict[str, Any]]:
    """List all available job types that can be scheduled."""
    available = []
    
    for job_id in JOB_FUNCTIONS:
        config = get_job_config(job_id)
        if config:
            available.append({
                "job_id": job_id,
                "name": config.name,
                "description": config.metadata.get("description", ""),
                "default_cron": config.cron_expression,
                "default_enabled": config.enabled,
            })
    
    return available
