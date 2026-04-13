"""Memory API router for debugging and inspection."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies import get_db_session
from app.contracts.dto.memory import (
    EntityMemoryDTO,
    JudgementMemoryDTO,
    MemoryRetrievalResultDTO,
    TimelinePointDTO,
    TopicHistoryContextDTO,
    TopicMemoryDTO,
    TopicSnapshotDTO,
)
from app.memory.repositories.entity_memory_repository import EntityMemoryRepository
from app.memory.repositories.judgement_repository import JudgementRepository
from app.memory.repositories.topic_memory_repository import TopicMemoryRepository
from app.memory.service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


class JudgementListResponse(BaseModel):
    """Response for judgement list."""

    judgements: list[JudgementMemoryDTO]
    count: int


async def get_memory_service(
    session=Depends(get_db_session),
) -> MemoryService:
    """Get memory service dependency."""
    topic_memory_repo = TopicMemoryRepository(session)
    entity_memory_repo = EntityMemoryRepository(session)
    judgement_repo = JudgementRepository(session)
    return MemoryService(
        topic_memory_repo=topic_memory_repo,
        entity_memory_repo=entity_memory_repo,
        judgement_repo=judgement_repo,
    )


# ============ Topic Memory Endpoints ============


@router.get("/topics/{topic_id}/memory", response_model=TopicMemoryDTO | None)
async def get_topic_memory(
    topic_id: int,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> TopicMemoryDTO | None:
    """Get topic memory.

    Args:
        topic_id: Topic ID.
        service: Memory service.

    Returns:
        TopicMemoryDTO if exists.
    """
    return await service.get_topic_memory(topic_id)


@router.get("/topics/{topic_id}/snapshots", response_model=list[TopicSnapshotDTO])
async def get_topic_snapshots(
    topic_id: int,
    service: Annotated[MemoryService, Depends(get_memory_service)],
    limit: int = Query(default=10, ge=1, le=100),
) -> list[TopicSnapshotDTO]:
    """Get topic snapshots.

    Args:
        topic_id: Topic ID.
        service: Memory service.
        limit: Maximum number of snapshots.

    Returns:
        List of TopicSnapshotDTO.
    """
    return await service.get_topic_snapshots(topic_id, limit=limit)


@router.get("/topics/{topic_id}/context", response_model=TopicHistoryContextDTO)
async def get_topic_context(
    topic_id: int,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> TopicHistoryContextDTO:
    """Get complete topic historical context.

    Args:
        topic_id: Topic ID.
        service: Memory service.

    Returns:
        TopicHistoryContextDTO with all context.
    """
    return await service.retrieve_topic_context(topic_id)


@router.get("/topics/{topic_id}/full-context", response_model=MemoryRetrievalResultDTO)
async def get_topic_full_context(
    topic_id: int,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> MemoryRetrievalResultDTO:
    """Get full memory retrieval result for a topic.

    Args:
        topic_id: Topic ID.
        service: Memory service.

    Returns:
        MemoryRetrievalResultDTO with all memory data.
    """
    return await service.get_topic_historical_context(topic_id)


# ============ Entity Memory Endpoints ============


@router.get("/entities/{entity_id}/memory", response_model=EntityMemoryDTO | None)
async def get_entity_memory(
    entity_id: int,
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> EntityMemoryDTO | None:
    """Get entity memory.

    Args:
        entity_id: Entity ID.
        service: Memory service.

    Returns:
        EntityMemoryDTO if exists.
    """
    return await service.get_entity_memory(entity_id)


@router.get("/entities/{entity_id}/related-topics", response_model=list[int])
async def get_entity_related_topics(
    entity_id: int,
    service: Annotated[MemoryService, Depends(get_memory_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> list[int]:
    """Get topics related to an entity.

    Args:
        entity_id: Entity ID.
        service: Memory service.
        limit: Maximum number of topics.

    Returns:
        List of topic IDs.
    """
    return await service.get_entity_related_topics(entity_id, limit=limit)


# ============ Judgement Endpoints ============


@router.get("/judgements/{target_type}/{target_id}", response_model=JudgementListResponse)
async def get_judgements_for_target(
    target_type: str,
    target_id: int,
    service: Annotated[MemoryService, Depends(get_memory_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> JudgementListResponse:
    """Get judgements for a target.

    Args:
        target_type: Type of target (topic, entity, item).
        target_id: ID of the target.
        service: Memory service.
        limit: Maximum number of judgements.

    Returns:
        JudgementListResponse with judgements.
    """
    if target_type not in ("topic", "entity", "item"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid target_type: {target_type}. Must be topic, entity, or item.",
        )

    judgements = await service.get_judgements_for_target(target_type, target_id, limit=limit)
    return JudgementListResponse(
        judgements=judgements,
        count=len(judgements),
    )


@router.get("/judgements/by-type/{judgement_type}", response_model=JudgementListResponse)
async def get_judgements_by_type(
    judgement_type: str,
    service: Annotated[MemoryService, Depends(get_memory_service)],
    limit: int = Query(default=20, ge=1, le=100),
) -> JudgementListResponse:
    """Get recent judgements by type.

    Args:
        judgement_type: Type of judgement.
        service: Memory service.
        limit: Maximum number of judgements.

    Returns:
        JudgementListResponse with judgements.
    """
    judgements = await service.get_recent_judgements_by_type(judgement_type, limit=limit)
    return JudgementListResponse(
        judgements=judgements,
        count=len(judgements),
    )


# ============ Debug Endpoints ============


@router.get("/debug/stats")
async def get_memory_stats(
    session=Depends(get_db_session),
) -> dict[str, Any]:
    """Get memory system statistics.

    Returns:
        Dictionary with memory stats.
    """
    from sqlalchemy import func, select

    from app.storage.db.models.entity import Entity
    from app.storage.db.models.entity_memory import EntityMemory
    from app.storage.db.models.judgement_log import JudgementLog
    from app.storage.db.models.topic_memory import TopicMemory
    from app.storage.db.models.topic_snapshot import TopicSnapshot

    # Count records
    topic_memory_count = await session.scalar(select(func.count()).select_from(TopicMemory))
    topic_snapshot_count = await session.scalar(select(func.count()).select_from(TopicSnapshot))
    entity_count = await session.scalar(select(func.count()).select_from(Entity))
    entity_memory_count = await session.scalar(select(func.count()).select_from(EntityMemory))
    judgement_count = await session.scalar(select(func.count()).select_from(JudgementLog))

    return {
        "topic_memories": topic_memory_count or 0,
        "topic_snapshots": topic_snapshot_count or 0,
        "entities": entity_count or 0,
        "entity_memories": entity_memory_count or 0,
        "judgements": judgement_count or 0,
    }


# ============ Timeline Endpoints ============


@router.get("/topics/{topic_id}/timeline", response_model=list[TimelinePointDTO])
async def get_topic_timeline(
    topic_id: int,
    session=Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TimelinePointDTO]:
    """Get timeline for a topic.

    Args:
        topic_id: Topic ID.
        session: Database session.
        limit: Maximum number of events.

    Returns:
        List of TimelinePointDTO.
    """
    from app.contracts.dto.memory import TimelinePointDTO
    from app.memory.repositories.timeline_repository import TimelineRepository

    timeline_repo = TimelineRepository(session)
    events = await timeline_repo.list_by_topic(topic_id, limit=limit)

    return [
        TimelinePointDTO(
            event_time=e.event_time,
            event_type=e.event_type,
            title=e.title,
            description=e.description,
            source_item_id=e.source_item_id,
            source_type=e.source_type,
            importance_score=e.importance_score,
            metadata=e.metadata,
        )
        for e in events
    ]


@router.get("/topics/{topic_id}/milestones", response_model=list[TimelinePointDTO])
async def get_topic_milestones(
    topic_id: int,
    session=Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[TimelinePointDTO]:
    """Get milestone events for a topic.

    Args:
        topic_id: Topic ID.
        session: Database session.
        limit: Maximum number of milestones.

    Returns:
        List of milestone TimelinePointDTO.
    """
    from app.contracts.dto.memory import TimelinePointDTO
    from app.memory.repositories.timeline_repository import TimelineRepository

    timeline_repo = TimelineRepository(session)
    events = await timeline_repo.list_milestones(topic_id, limit=limit)

    return [
        TimelinePointDTO(
            event_time=e.event_time,
            event_type=e.event_type,
            title=e.title,
            description=e.description,
            source_item_id=e.source_item_id,
            source_type=e.source_type,
            importance_score=e.importance_score,
            metadata=e.metadata,
        )
        for e in events
    ]


@router.post("/topics/{topic_id}/timeline/refresh")
async def refresh_topic_timeline(
    topic_id: int,
    session=Depends(get_db_session),
) -> dict[str, Any]:
    """Refresh timeline for a topic.

    Args:
        topic_id: Topic ID.
        session: Database session.

    Returns:
        Refresh result with event count.
    """
    from app.memory.repositories.timeline_repository import TimelineRepository
    from app.memory.timeline.service import TimelineService
    from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
    from app.storage.repositories.topic_repository import TopicRepository

    timeline_repo = TimelineRepository(session)
    topic_repo = TopicRepository(session)
    item_repo = NormalizedItemRepository(session)

    service = TimelineService(
        timeline_repo=timeline_repo,
        topic_repo=topic_repo,
        item_repo=item_repo,
    )

    events = await service.refresh_topic_timeline(topic_id)

    return {
        "topic_id": topic_id,
        "event_count": len(events),
        "success": True,
    }


@router.get("/topics/{topic_id}/history-context", response_model=TopicHistoryContextDTO)
async def get_topic_history_context(
    topic_id: int,
    session=Depends(get_db_session),
) -> TopicHistoryContextDTO:
    """Get complete historical context for a topic.

    Uses the retrieval service to gather all relevant context.

    Args:
        topic_id: Topic ID.
        session: Database session.

    Returns:
        TopicHistoryContextDTO with all context.
    """
    from app.memory.repositories.timeline_repository import TimelineRepository
    from app.memory.retrieval.service import MemoryRetrievalService

    topic_memory_repo = TopicMemoryRepository(session)
    entity_memory_repo = EntityMemoryRepository(session)
    judgement_repo = JudgementRepository(session)
    timeline_repo = TimelineRepository(session)

    retrieval_service = MemoryRetrievalService(
        topic_memory_repo=topic_memory_repo,
        entity_memory_repo=entity_memory_repo,
        judgement_repo=judgement_repo,
        timeline_repo=timeline_repo,
    )

    return await retrieval_service.retrieve_topic_history(topic_id)
