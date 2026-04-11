"""FastAPI application entry point."""

from typing import Annotated

from fastapi import Depends, FastAPI

from app.api.dependencies import get_app_settings
from app.api.routers.debug import router as debug_router
from app.api.routers.source import router as source_router
from app.bootstrap.lifecycle import lifespan
from app.bootstrap.logging import get_logger
from app.bootstrap.settings import Settings

logger = get_logger(__name__)

app = FastAPI(
    title="NewsAgent",
    description="AI-powered news aggregation and topic analysis system",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(source_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")


@app.get("/health")
async def health_check(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, str | bool]:
    """Health check endpoint with app info."""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "app_name": settings.app.name,
        "environment": settings.app.env,
        "debug": settings.app.debug,
    }
