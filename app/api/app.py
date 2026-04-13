"""FastAPI application entry point."""

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import get_app_settings
from app.api.routers.admin import router as admin_router
from app.api.routers.debug import router as debug_router
from app.api.routers.feed import router as feed_router
from app.api.routers.memory import router as memory_router
from app.api.routers.ranking import router as ranking_router
from app.api.routers.reports import router as reports_router
from app.api.routers.scheduler import router as scheduler_router
from app.api.routers.search import router as search_router
from app.api.routers.source import router as source_router
from app.api.routers.subscription import router as subscription_router
from app.api.routers.topics import router as topics_router
from app.api.routers.trends import router as trends_router
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

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - API v1
app.include_router(source_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(feed_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(topics_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(subscription_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(ranking_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")


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
