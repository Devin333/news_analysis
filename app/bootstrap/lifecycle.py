"""Application lifecycle management."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.bootstrap.logging import get_logger, setup_logging
from app.bootstrap.settings import get_settings
from app.collectors.setup import setup_collectors
from app.common.exceptions import InfrastructureError
from app.scheduler.manager import SchedulerManager
from app.storage.db.session import ping_database

logger = get_logger(__name__)


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
    scheduler = SchedulerManager()
    if settings.app.env != "testing":
        scheduler.start()
        logger.info("Scheduler started")

    yield

    # Shutdown
    if scheduler.is_running:
        scheduler.stop()
        logger.info("Scheduler stopped")
    logger.info("Application shutting down")
