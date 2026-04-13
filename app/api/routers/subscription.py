"""Subscription API router.

Provides endpoints for subscription management.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.bootstrap.logging import get_logger
from app.contracts.dto.subscription import (
    MatchMode,
    NotifyFrequency,
    SubscriptionCreateDTO,
    SubscriptionMatchDTO,
    SubscriptionReadDTO,
    SubscriptionStatus,
    SubscriptionType,
    SubscriptionUpdateDTO,
)
from app.storage.repositories.subscription_repository import (
    SubscriptionEventRepository,
    SubscriptionRepository,
)
from app.subscription.matcher import SubscriptionMatcher
from app.subscription.service import SubscriptionService

logger = get_logger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# Request/Response schemas
class CreateSubscriptionRequest(BaseModel):
    """Request to create a subscription."""

    subscription_type: SubscriptionType
    user_key: str
    query: str | None = None
    tags: list[str] = Field(default_factory=list)
    board_type: str | None = None
    entity_id: int | None = None
    topic_id: int | None = None
    name: str | None = None
    notify_email: bool = True
    notify_frequency: NotifyFrequency = NotifyFrequency.DAILY
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    match_mode: MatchMode = MatchMode.ANY


class UpdateSubscriptionRequest(BaseModel):
    """Request to update a subscription."""

    name: str | None = None
    status: SubscriptionStatus | None = None
    notify_email: bool | None = None
    notify_frequency: NotifyFrequency | None = None
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    match_mode: MatchMode | None = None
    query: str | None = None
    tags: list[str] | None = None


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: int
    subscription_type: str
    user_key: str
    query: str | None = None
    tags: list[str] = Field(default_factory=list)
    board_type: str | None = None
    entity_id: int | None = None
    topic_id: int | None = None
    name: str | None = None
    status: str
    notify_email: bool
    notify_frequency: str
    min_score: float
    match_mode: str
    created_at: datetime
    updated_at: datetime
    last_matched_at: datetime | None = None
    match_count: int = 0
    unread_count: int = 0


class SubscriptionListResponse(BaseModel):
    """List subscriptions response."""

    user_key: str
    subscriptions: list[SubscriptionResponse]
    total: int
    filters: dict[str, Any] = Field(default_factory=dict)


class MatchEventResponse(BaseModel):
    """Match event response."""

    id: int
    subscription_id: int
    target_type: str
    target_id: int
    target_title: str | None = None
    target_summary: str | None = None
    match_score: float
    match_reason: str | None = None
    matched_fields: list[str] = Field(default_factory=list)
    matched_tags: list[str] = Field(default_factory=list)
    notification_status: str
    is_read: bool
    created_at: datetime


class MatchListResponse(BaseModel):
    """List matches response."""

    subscription_id: int
    matches: list[MatchEventResponse]
    total: int
    unread_count: int


class UnreadMatchesResponse(BaseModel):
    """Unread matches response."""

    user_key: str
    matches: list[MatchEventResponse]
    total: int


def _get_subscription_service(session: AsyncSession) -> SubscriptionService:
    """Create subscription service with dependencies."""
    subscription_repo = SubscriptionRepository(session)
    event_repo = SubscriptionEventRepository(session)
    matcher = SubscriptionMatcher()
    return SubscriptionService(
        subscription_repo=subscription_repo,
        event_repo=event_repo,
        matcher=matcher,
    )


def _dto_to_response(dto: SubscriptionReadDTO) -> SubscriptionResponse:
    """Convert DTO to response."""
    return SubscriptionResponse(
        id=dto.id,
        subscription_type=dto.subscription_type.value,
        user_key=dto.user_key,
        query=dto.query,
        tags=dto.tags,
        board_type=dto.board_type,
        entity_id=dto.entity_id,
        topic_id=dto.topic_id,
        name=dto.name,
        status=dto.status.value,
        notify_email=dto.notify_email,
        notify_frequency=dto.notify_frequency.value,
        min_score=dto.min_score,
        match_mode=dto.match_mode.value,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        last_matched_at=dto.last_matched_at,
        match_count=dto.match_count,
        unread_count=dto.unread_count,
    )


def _match_dto_to_response(dto: SubscriptionMatchDTO) -> MatchEventResponse:
    """Convert match DTO to response."""
    return MatchEventResponse(
        id=dto.id,
        subscription_id=dto.subscription_id,
        target_type=dto.target_type,
        target_id=dto.target_id,
        target_title=dto.target_title,
        target_summary=dto.target_summary,
        match_score=dto.match_score,
        match_reason=dto.match_reason,
        matched_fields=dto.matched_fields,
        matched_tags=dto.matched_tags,
        notification_status=dto.notification_status,
        is_read=dto.is_read,
        created_at=dto.created_at,
    )


@router.post("", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionResponse:
    """Create a new subscription.

    Args:
        request: Subscription creation request.
        session: Database session.

    Returns:
        Created subscription.
    """
    service = _get_subscription_service(session)

    create_dto = SubscriptionCreateDTO(
        subscription_type=request.subscription_type,
        user_key=request.user_key,
        query=request.query,
        tags=request.tags,
        board_type=request.board_type,
        entity_id=request.entity_id,
        topic_id=request.topic_id,
        name=request.name,
        notify_email=request.notify_email,
        notify_frequency=request.notify_frequency,
        min_score=request.min_score,
        match_mode=request.match_mode,
    )

    result = await service.create_subscription(create_dto)
    logger.info(f"Created subscription {result.id} for user {request.user_key}")
    return _dto_to_response(result)


@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions(
    user_key: str,
    status: SubscriptionStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionListResponse:
    """List subscriptions for a user.

    Args:
        user_key: User identifier.
        status: Optional status filter.
        limit: Maximum subscriptions.
        session: Database session.

    Returns:
        List of subscriptions.
    """
    service = _get_subscription_service(session)

    subscriptions = await service.list_subscriptions(
        user_key,
        status=status,
        limit=limit,
    )

    return SubscriptionListResponse(
        user_key=user_key,
        subscriptions=[_dto_to_response(s) for s in subscriptions],
        total=len(subscriptions),
        filters={"status": status.value if status else None},
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionResponse:
    """Get a subscription by ID.

    Args:
        subscription_id: Subscription ID.
        session: Database session.

    Returns:
        Subscription details.
    """
    service = _get_subscription_service(session)

    result = await service.get_subscription(subscription_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return _dto_to_response(result)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    request: UpdateSubscriptionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionResponse:
    """Update a subscription.

    Args:
        subscription_id: Subscription ID.
        request: Update request.
        session: Database session.

    Returns:
        Updated subscription.
    """
    service = _get_subscription_service(session)

    update_dto = SubscriptionUpdateDTO(
        name=request.name,
        status=request.status,
        notify_email=request.notify_email,
        notify_frequency=request.notify_frequency,
        min_score=request.min_score,
        match_mode=request.match_mode,
        query=request.query,
        tags=request.tags,
    )

    result = await service.update_subscription(subscription_id, update_dto)
    if result is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return _dto_to_response(result)


@router.post("/{subscription_id}/disable", response_model=dict)
async def disable_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Disable a subscription.

    Args:
        subscription_id: Subscription ID.
        session: Database session.

    Returns:
        Disable confirmation.
    """
    service = _get_subscription_service(session)

    success = await service.disable_subscription(subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "id": subscription_id,
        "status": "disabled",
        "disabled_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/{subscription_id}/enable", response_model=dict)
async def enable_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Enable a subscription.

    Args:
        subscription_id: Subscription ID.
        session: Database session.

    Returns:
        Enable confirmation.
    """
    service = _get_subscription_service(session)

    update_dto = SubscriptionUpdateDTO(status=SubscriptionStatus.ACTIVE)
    result = await service.update_subscription(subscription_id, update_dto)
    if result is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "id": subscription_id,
        "status": "active",
        "enabled_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/{subscription_id}", response_model=dict)
async def delete_subscription(
    subscription_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Delete a subscription.

    Args:
        subscription_id: Subscription ID.
        session: Database session.

    Returns:
        Deletion confirmation.
    """
    service = _get_subscription_service(session)

    success = await service.delete_subscription(subscription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "id": subscription_id,
        "deleted": True,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{subscription_id}/matches", response_model=MatchListResponse)
async def get_subscription_matches(
    subscription_id: int,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> MatchListResponse:
    """Get match events for a subscription.

    Args:
        subscription_id: Subscription ID.
        unread_only: Only return unread matches.
        limit: Maximum matches.
        session: Database session.

    Returns:
        List of match events.
    """
    service = _get_subscription_service(session)

    # Verify subscription exists
    subscription = await service.get_subscription(subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    matches = await service.get_subscription_matches(
        subscription_id,
        unread_only=unread_only,
        limit=limit,
    )

    unread_count = sum(1 for m in matches if not m.is_read)

    return MatchListResponse(
        subscription_id=subscription_id,
        matches=[_match_dto_to_response(m) for m in matches],
        total=len(matches),
        unread_count=unread_count,
    )


@router.post("/{subscription_id}/matches/{match_id}/read", response_model=dict)
async def mark_match_as_read(
    subscription_id: int,
    match_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Mark a match as read.

    Args:
        subscription_id: Subscription ID.
        match_id: Match event ID.
        session: Database session.

    Returns:
        Updated match.
    """
    service = _get_subscription_service(session)

    success = await service.mark_match_as_read(match_id)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found")

    return {
        "id": match_id,
        "subscription_id": subscription_id,
        "is_read": True,
        "read_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/user/{user_key}/unread", response_model=UnreadMatchesResponse)
async def get_unread_matches(
    user_key: str,
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> UnreadMatchesResponse:
    """Get all unread matches for a user.

    Args:
        user_key: User identifier.
        limit: Maximum matches.
        session: Database session.

    Returns:
        List of unread matches across all subscriptions.
    """
    service = _get_subscription_service(session)

    # Get user's subscriptions
    subscriptions = await service.list_subscriptions(user_key, limit=100)

    all_matches: list[SubscriptionMatchDTO] = []
    for sub in subscriptions:
        matches = await service.get_subscription_matches(
            sub.id,
            unread_only=True,
            limit=limit,
        )
        all_matches.extend(matches)

    # Sort by created_at descending and limit
    all_matches.sort(key=lambda m: m.created_at, reverse=True)
    all_matches = all_matches[:limit]

    return UnreadMatchesResponse(
        user_key=user_key,
        matches=[_match_dto_to_response(m) for m in all_matches],
        total=len(all_matches),
    )


@router.post("/match/topic/{topic_id}", response_model=dict)
async def match_topic(
    topic_id: int,
    topic_title: str,
    topic_summary: str | None = None,
    topic_tags: list[str] | None = Query(None),
    board_type: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Manually trigger matching a topic against all subscriptions.

    Args:
        topic_id: Topic ID.
        topic_title: Topic title.
        topic_summary: Topic summary.
        topic_tags: Topic tags.
        board_type: Topic board type.
        session: Database session.

    Returns:
        Match result.
    """
    service = _get_subscription_service(session)

    result = await service.match_topic_against_subscriptions(
        topic_id=topic_id,
        topic_title=topic_title,
        topic_summary=topic_summary,
        topic_tags=topic_tags,
        board_type=board_type,
    )

    return {
        "content_type": result.content_type,
        "content_id": result.content_id,
        "matched_subscriptions": result.matched_subscriptions,
        "match_details": result.match_details,
        "total_matches": result.total_matches,
    }
