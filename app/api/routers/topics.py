"""Topic API router for topic management and debugging."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies import get_db_session
from app.common.enums import BoardType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.tag import TopicTagDTO
from app.contracts.dto.topic import TopicReadDTO, TopicSummaryDTO
from app.editorial.topic_service import TopicService
from app.frontend_contracts.topic_view import (
    TopicDetailView,
    TopicHistorianOutputView,
    build_topic_detail_view,
)
from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
from app.storage.repositories.tag_repository import TagRepository
from app.storage.repositories.topic_repository import TopicRepository

router = APIRouter(prefix="/topics", tags=["topics"])


class TopicDetailResponse(BaseModel):
    """Enhanced topic detail response."""

    topic: TopicReadDTO
    tags: list[TopicTagDTO] = []
    representative_item: NormalizedItemDTO | None = None
    item_ids: list[int] = []


class TopicEnrichRequest(BaseModel):
    """Request for topic enrichment."""

    refresh_tags: bool = True
    refresh_metrics: bool = True
    refresh_summary: bool = False


async def get_topic_service(
    session=Depends(get_db_session),
) -> TopicService:
    """Get topic service dependency."""
    topic_repo = TopicRepository(session)
    item_repo = NormalizedItemRepository(session)
    return TopicService(topic_repo, item_repo)


async def get_tag_repository(
    session=Depends(get_db_session),
) -> TagRepository:
    """Get tag repository dependency."""
    return TagRepository(session)


@router.get("", response_model=list[TopicSummaryDTO])
async def list_topics(
    service: Annotated[TopicService, Depends(get_topic_service)],
    limit: int = Query(default=50, ge=1, le=200),
    board_type: BoardType | None = None,
) -> list[TopicSummaryDTO]:
    """List recent topics.

    Args:
        service: Topic service.
        limit: Maximum number of topics to return.
        board_type: Optional filter by board type.

    Returns:
        List of topic summaries.
    """
    if board_type:
        topics = await service.list_topics_by_board(board_type, limit=limit)
        # Convert to summaries
        return [
            TopicSummaryDTO(
                id=t.id,
                title=t.title,
                board_type=t.board_type,
                item_count=t.item_count,
                source_count=t.source_count,
                heat_score=t.heat_score,
                last_seen_at=t.last_seen_at,
            )
            for t in topics
        ]
    return await service.list_topic_summaries(limit=limit)


@router.get("/{topic_id}", response_model=TopicReadDTO)
async def get_topic(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> TopicReadDTO:
    """Get topic by ID.

    Args:
        topic_id: Topic ID.
        service: Topic service.

    Returns:
        Topic details.

    Raises:
        HTTPException: If topic not found.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.get("/{topic_id}/items", response_model=list[int])
async def get_topic_items(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[int]:
    """Get item IDs for a topic.

    Args:
        topic_id: Topic ID.
        service: Topic service.
        limit: Maximum number of items to return.

    Returns:
        List of item IDs.
    """
    # Verify topic exists
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    return await service.get_topic_items(topic_id, limit=limit)


@router.post("/{topic_id}/refresh-metrics")
async def refresh_topic_metrics(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> dict:
    """Refresh topic metrics.

    Args:
        topic_id: Topic ID.
        service: Topic service.

    Returns:
        Success status.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    success = await service.update_topic_metrics(topic_id)
    return {"success": success, "topic_id": topic_id}


@router.post("/{topic_id}/refresh-summary")
async def refresh_topic_summary(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> dict:
    """Refresh topic summary stub.

    Args:
        topic_id: Topic ID.
        service: Topic service.

    Returns:
        New summary.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    summary = await service.build_topic_summary_stub(topic_id)
    return {"topic_id": topic_id, "summary": summary}


@router.post("/{topic_id}/recompute-representative")
async def recompute_representative_item(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
) -> dict:
    """Recompute representative item for topic.

    Args:
        topic_id: Topic ID.
        service: Topic service.

    Returns:
        New representative item ID.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    representative_id = await service.recompute_representative_item(topic_id)
    return {"topic_id": topic_id, "representative_item_id": representative_id}


@router.get("/{topic_id}/detail", response_model=TopicDetailResponse)
async def get_topic_detail(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
    tag_repo: Annotated[TagRepository, Depends(get_tag_repository)],
    session=Depends(get_db_session),
) -> TopicDetailResponse:
    """Get enhanced topic detail with tags and representative item.

    Args:
        topic_id: Topic ID.
        service: Topic service.
        tag_repo: Tag repository.
        session: Database session.

    Returns:
        Enhanced topic detail.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get topic tags
    tags = await tag_repo.get_topic_tags(topic_id)

    # Get item IDs
    item_ids = await service.get_topic_items(topic_id, limit=100)

    # Get representative item if exists
    representative_item = None
    if topic.representative_item_id:
        item_repo = NormalizedItemRepository(session)
        representative_item = await item_repo.get_by_id(topic.representative_item_id)

    return TopicDetailResponse(
        topic=topic,
        tags=tags,
        representative_item=representative_item,
        item_ids=item_ids,
    )


@router.get("/{topic_id}/tags", response_model=list[TopicTagDTO])
async def get_topic_tags(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
    tag_repo: Annotated[TagRepository, Depends(get_tag_repository)],
) -> list[TopicTagDTO]:
    """Get tags for a topic.

    Args:
        topic_id: Topic ID.
        service: Topic service.
        tag_repo: Tag repository.

    Returns:
        List of topic tags.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    return await tag_repo.get_topic_tags(topic_id)


@router.post("/{topic_id}/refresh-tags")
async def refresh_topic_tags(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
    tag_repo: Annotated[TagRepository, Depends(get_tag_repository)],
) -> dict[str, Any]:
    """Refresh tags for a topic by aggregating item tags.

    Args:
        topic_id: Topic ID.
        service: Topic service.
        tag_repo: Tag repository.

    Returns:
        Refresh result with tag count.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    tags = await service.refresh_topic_tags(topic_id, tag_repo=tag_repo)

    return {
        "topic_id": topic_id,
        "tag_count": len(tags),
        "tags": [{"name": t.tag_name, "type": t.tag_type} for t in tags],
    }


@router.post("/{topic_id}/enrich")
async def enrich_topic(
    topic_id: int,
    request: TopicEnrichRequest,
    service: Annotated[TopicService, Depends(get_topic_service)],
    tag_repo: Annotated[TagRepository, Depends(get_tag_repository)],
) -> dict[str, Any]:
    """Enrich a topic with tags, metrics, and summary.

    Args:
        topic_id: Topic ID.
        request: Enrichment options.
        service: Topic service.
        tag_repo: Tag repository.

    Returns:
        Enrichment result.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    result: dict[str, Any] = {"topic_id": topic_id}

    if request.refresh_tags:
        tags = await service.refresh_topic_tags(topic_id, tag_repo=tag_repo)
        result["tags_refreshed"] = len(tags)

    if request.refresh_metrics:
        await service.update_topic_metrics(topic_id)
        result["metrics_refreshed"] = True

    if request.refresh_summary:
        summary = await service.build_topic_summary_stub(topic_id)
        result["summary"] = summary

    return result


@router.get("/{topic_id}/enriched", response_model=TopicDetailView)
async def get_enriched_topic_detail(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
    tag_repo: Annotated[TagRepository, Depends(get_tag_repository)],
    session=Depends(get_db_session),
) -> TopicDetailView:
    """Get enriched topic detail with historical context.

    Returns topic with historian output and tags.

    Args:
        topic_id: Topic ID.
        service: Topic service.
        tag_repo: Tag repository.
        session: Database session.

    Returns:
        Enriched topic detail view.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get topic tags
    tags = await tag_repo.get_topic_tags(topic_id)
    tag_names = [t.tag_name for t in tags]

    # Get representative item
    representative_item = None
    if topic.representative_item_id:
        item_repo = NormalizedItemRepository(session)
        representative_item = await item_repo.get_by_id(topic.representative_item_id)

    # Get historian output from topic memory
    historian_output = None
    try:
        from app.memory.repositories.topic_memory_repository import TopicMemoryRepository
        
        memory_repo = TopicMemoryRepository(session)
        memory = await memory_repo.get_by_topic_id(topic_id)
        if memory:
            # Get raw model to access historian output
            from sqlalchemy import select
            from app.storage.db.models.topic_memory import TopicMemory
            
            stmt = select(TopicMemory).where(TopicMemory.topic_id == topic_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model and model.latest_historian_output_json:
                historian_output = model.latest_historian_output_json
    except Exception:
        pass  # Historian output not available

    return build_topic_detail_view(
        topic=topic,
        historian_output=historian_output,
        representative_item=representative_item,
        tags=tag_names,
    )


@router.get("/{topic_id}/historian-output", response_model=TopicHistorianOutputView)
async def get_topic_historian_output(
    topic_id: int,
    service: Annotated[TopicService, Depends(get_topic_service)],
    session=Depends(get_db_session),
) -> TopicHistorianOutputView:
    """Get historian output for a topic.

    Args:
        topic_id: Topic ID.
        service: Topic service.
        session: Database session.

    Returns:
        Historian output view.
    """
    topic = await service.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get historian output from topic memory
    historian_output = None
    try:
        from sqlalchemy import select
        from app.storage.db.models.topic_memory import TopicMemory
        
        stmt = select(TopicMemory).where(TopicMemory.topic_id == topic_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model and model.latest_historian_output_json:
            historian_output = model.latest_historian_output_json
    except Exception:
        pass

    if historian_output is None:
        raise HTTPException(
            status_code=404,
            detail="Historian output not available for this topic"
        )

    # Build timeline points
    from app.frontend_contracts.topic_view import TimelinePointView
    
    timeline_points = []
    if historian_output.get("timeline_points"):
        for tp in historian_output["timeline_points"]:
            timeline_points.append(TimelinePointView(
                event_time=tp.get("event_time"),
                event_type=tp.get("event_type", "unknown"),
                title=tp.get("title", ""),
                description=tp.get("description"),
                importance=tp.get("importance", 0.5),
            ))

    return TopicHistorianOutputView(
        topic_id=topic_id,
        first_seen_at=historian_output.get("first_seen_at"),
        last_seen_at=historian_output.get("last_seen_at"),
        historical_status=historian_output.get("historical_status"),
        current_stage=historian_output.get("current_stage"),
        history_summary=historian_output.get("history_summary"),
        what_is_new_this_time=historian_output.get("what_is_new_this_time"),
        timeline_points=timeline_points,
        similar_past_topics=[
            t.get("topic_id") for t in historian_output.get("similar_past_topics", [])
            if t.get("topic_id")
        ],
        important_background=historian_output.get("important_background"),
        historical_confidence=historian_output.get("historical_confidence"),
        evidence_sources=historian_output.get("evidence_sources", []),
    )
