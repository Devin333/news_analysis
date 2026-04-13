"""Trends API router.

Provides endpoints for trend data, wired to database.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.bootstrap.logging import get_logger
from app.frontend_contracts.trend_view import (
    TrendCardView,
    TrendPageView,
    TrendSectionView,
    TrendSignalView,
)
from app.storage.db.models.trend_signal import TrendSignal
from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/trends", tags=["trends"])


def _topic_to_trend_card(topic, signals: list[TrendSignal] | None = None) -> TrendCardView:
    """Convert a TopicReadDTO + signals to a TrendCardView."""
    signal_views = []
    stage_label = "stable"
    watch_points: list[str] = []

    if signals:
        for sig in signals:
            evidence = sig.evidence_json or []
            signal_views.append(TrendSignalView(
                signal_type=sig.signal_type,
                strength=sig.signal_strength,
                description=f"{sig.signal_type} signal (strength: {sig.signal_strength:.2f})",
                evidence=[str(e) for e in evidence[:3]],
            ))
            if sig.stage_label:
                stage_label = sig.stage_label

    trend_score = float(topic.trend_score)
    heat_score = float(topic.heat_score)

    # Determine direction based on trend_score
    if trend_score > 60:
        direction = "up"
    elif trend_score < 30:
        direction = "down"
    else:
        direction = "stable"

    return TrendCardView(
        topic_id=topic.id,
        trend_title=topic.title,
        trend_summary=topic.summary or "",
        signal_summary=f"{len(signal_views)} signals detected" if signal_views else "No signals",
        stage_label=stage_label,
        trend_score=trend_score,
        heat_score=heat_score,
        signals=signal_views,
        watch_points=watch_points,
        trend_direction=direction,
        confidence=min(trend_score / 100.0, 1.0),
        last_updated=topic.last_seen_at,
    )


async def _get_topic_signals(
    session: AsyncSession, topic_id: int, limit: int = 10
) -> list[TrendSignal]:
    """Get trend signals for a topic."""
    try:
        result = await session.execute(
            select(TrendSignal)
            .where(TrendSignal.topic_id == topic_id)
            .where(TrendSignal.status == "active")
            .order_by(TrendSignal.detected_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    except Exception:
        return []


@router.get("")
async def list_trends(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    stage: str | None = Query(default=None, description="Filter by trend stage"),
    time_window_hours: int = Query(default=72, ge=1, le=168, description="Time window"),
) -> TrendPageView:
    """List current trends ranked by trend signals."""
    topic_repo = TopicRepository(session)
    topics = await topic_repo.list_recent(limit=limit * 2)

    # Sort by trend_score descending
    topics.sort(key=lambda t: float(t.trend_score), reverse=True)
    topics = topics[:limit]

    # Build trend cards with signals
    emerging: list[TrendCardView] = []
    rising: list[TrendCardView] = []
    stable: list[TrendCardView] = []

    for topic in topics:
        signals = await _get_topic_signals(session, topic.id)
        card = _topic_to_trend_card(topic, signals)

        # Categorize by stage
        if card.stage_label in ("emerging",):
            emerging.append(card)
        elif card.stage_label in ("rising", "growing"):
            rising.append(card)
        else:
            # Also categorize by trend_score if no explicit stage
            if float(topic.trend_score) > 70:
                emerging.append(card)
            elif float(topic.trend_score) > 40:
                rising.append(card)
            else:
                stable.append(card)

    # Filter by stage if requested
    if stage:
        if stage == "emerging":
            all_trends = emerging
        elif stage == "rising":
            all_trends = rising
        elif stage == "stable":
            all_trends = stable
        else:
            all_trends = emerging + rising + stable
    else:
        all_trends = emerging + rising + stable

    # Build sections
    sections: list[TrendSectionView] = []
    if emerging:
        sections.append(TrendSectionView(
            section_id="emerging",
            section_title="🔥 新兴趋势",
            section_description="刚刚出现的热门话题",
            trends=emerging,
            display_style="cards",
        ))
    if rising:
        sections.append(TrendSectionView(
            section_id="rising",
            section_title="📈 上升趋势",
            section_description="持续增长的话题",
            trends=rising,
            display_style="cards",
        ))
    if stable:
        sections.append(TrendSectionView(
            section_id="stable",
            section_title="📊 稳定趋势",
            section_description="持续关注的话题",
            trends=stable,
            display_style="list",
        ))

    return TrendPageView(
        emerging_trends=emerging,
        rising_trends=rising,
        stable_trends=stable,
        sections=sections,
        total_emerging=len(emerging),
        total_rising=len(rising),
        total_active=len(all_trends),
        last_updated=datetime.now(timezone.utc),
    )


@router.get("/emerging")
async def list_emerging_trends(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """List emerging trends."""
    topic_repo = TopicRepository(session)
    topics = await topic_repo.list_recent(limit=limit * 3)

    # Sort by trend_score descending, take top ones
    topics.sort(key=lambda t: float(t.trend_score), reverse=True)
    topics = topics[:limit]

    trends = []
    for topic in topics:
        signals = await _get_topic_signals(session, topic.id)
        card = _topic_to_trend_card(topic, signals)
        trends.append(card)

    return {
        "trends": [t.model_dump(mode="json") for t in trends],
        "total": len(trends),
        "stage": "emerging",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/rising")
async def list_rising_trends(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """List rising trends."""
    topic_repo = TopicRepository(session)
    topics = await topic_repo.list_recent(limit=limit * 3)

    # Sort by heat_score (rising = gaining heat)
    topics.sort(key=lambda t: float(t.heat_score), reverse=True)
    topics = topics[:limit]

    trends = []
    for topic in topics:
        signals = await _get_topic_signals(session, topic.id)
        card = _topic_to_trend_card(topic, signals)
        trends.append(card)

    return {
        "trends": [t.model_dump(mode="json") for t in trends],
        "total": len(trends),
        "stage": "rising",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/debug")
async def debug_trends() -> dict[str, Any]:
    """Debug endpoint for trend analysis."""
    return {
        "status": "ok",
        "trend_stages": ["emerging", "rising", "peak", "stable", "declining", "dormant"],
        "signal_types": ["growth", "diversity", "recency", "release", "discussion", "github", "repeated", "burst"],
        "thresholds": {
            "emerging": 0.6,
            "rising": 0.7,
            "peak": 0.85,
            "homepage": 0.75,
        },
    }


@router.get("/{topic_id}")
async def get_topic_trend(
    topic_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get trend analysis for a specific topic."""
    topic_repo = TopicRepository(session)
    topic = await topic_repo.get_by_id(topic_id)

    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    signals = await _get_topic_signals(session, topic_id)
    card = _topic_to_trend_card(topic, signals)

    return {
        "topic_id": topic_id,
        "is_emerging": card.stage_label in ("emerging",) or float(topic.trend_score) > 70,
        "trend_stage": card.stage_label,
        "trend_score": float(topic.trend_score),
        "signals": [s.model_dump(mode="json") for s in card.signals],
        "recommended_for_homepage": float(topic.heat_score) > 50,
        "watch_points": card.watch_points,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{topic_id}/signals")
async def get_topic_trend_signals(
    topic_id: int,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """Get trend signals for a topic."""
    signals = await _get_topic_signals(session, topic_id, limit=limit)

    signal_list = []
    for sig in signals:
        signal_list.append({
            "signal_type": sig.signal_type,
            "strength": sig.signal_strength,
            "stage_label": sig.stage_label,
            "evidence_count": sig.evidence_count,
            "detected_at": sig.detected_at.isoformat() if sig.detected_at else None,
            "window_start": sig.window_start.isoformat() if sig.window_start else None,
            "window_end": sig.window_end.isoformat() if sig.window_end else None,
        })

    return {
        "topic_id": topic_id,
        "signals": signal_list,
        "total": len(signal_list),
    }
