"""Feed API router.

Provides endpoints for ranked feeds, wired to FeedService and database.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.bootstrap.logging import get_logger
from app.common.enums import BoardType
from app.frontend_contracts.feed_view import (
    FeedItemView,
    FeedListView,
    FeedSectionView,
    HomeFeedView,
)
from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/feed", tags=["feed"])


def _topic_to_feed_item(topic) -> FeedItemView:
    """Convert a TopicReadDTO to a FeedItemView."""
    return FeedItemView(
        topic_id=topic.id,
        title=topic.title,
        short_summary=topic.summary or "",
        board_type=str(topic.board_type.value) if topic.board_type else None,
        item_count=topic.item_count,
        source_count=topic.source_count,
        heat_score=float(topic.heat_score),
        first_seen_at=topic.first_seen_at,
        last_updated_at=topic.last_seen_at,
        is_emerging=float(topic.trend_score) > 50.0,
        has_timeline=False,
        has_related_topics=False,
    )


@router.get("/news", response_model=FeedListView)
async def get_news_feed(
    session: AsyncSession = Depends(get_db_session),
    board_type: str | None = Query(None, description="Filter by board type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    time_window_hours: int = Query(48, ge=1, le=168, description="Time window in hours"),
    include_unreviewed: bool = Query(False, description="Include unreviewed topics"),
) -> FeedListView:
    """Get ranked news feed from database."""
    topic_repo = TopicRepository(session)

    if board_type:
        try:
            bt = BoardType(board_type)
            topics = await topic_repo.list_by_board(bt, limit=page_size * 3)
        except ValueError:
            topics = await topic_repo.list_recent(limit=page_size * 3)
    else:
        topics = await topic_repo.list_recent(limit=page_size * 3)

    # Sort by heat_score descending
    topics.sort(key=lambda t: float(t.heat_score), reverse=True)

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    page_topics = topics[start:end]

    items = [_topic_to_feed_item(t) for t in page_topics]
    total = len(topics)

    return FeedListView(
        items=items,
        total_count=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
        board_filter=board_type,
        sort_by="heat_score",
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/tech", response_model=FeedListView)
async def get_tech_feed(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    time_window_hours: int = Query(72, ge=1, le=168, description="Time window in hours"),
    include_unreviewed: bool = Query(True, description="Include unreviewed topics"),
) -> FeedListView:
    """Get ranked tech feed from database."""
    topic_repo = TopicRepository(session)

    # Get AI + engineering + research topics
    all_topics = []
    for bt in [BoardType.AI, BoardType.ENGINEERING, BoardType.RESEARCH]:
        topics = await topic_repo.list_by_board(bt, limit=page_size * 2)
        all_topics.extend(topics)

    # Sort by trend_score then heat_score
    all_topics.sort(
        key=lambda t: (float(t.trend_score), float(t.heat_score)),
        reverse=True,
    )

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    page_topics = all_topics[start:end]

    items = [_topic_to_feed_item(t) for t in page_topics]
    total = len(all_topics)

    return FeedListView(
        items=items,
        total_count=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
        sort_by="trend_score",
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/homepage", response_model=HomeFeedView)
async def get_homepage_feed(
    session: AsyncSession = Depends(get_db_session),
    max_items: int = Query(20, ge=1, le=50, description="Maximum items"),
) -> HomeFeedView:
    """Get homepage feed with sections and featured topic."""
    topic_repo = TopicRepository(session)

    # Get recent topics sorted by heat
    all_topics = await topic_repo.list_recent(limit=max_items * 2)
    all_topics.sort(key=lambda t: float(t.heat_score), reverse=True)

    # Featured topic: highest heat score
    featured_topic = None
    if all_topics:
        featured_topic = _topic_to_feed_item(all_topics[0])

    # Build sections by board type
    sections: list[FeedSectionView] = []

    board_labels = {
        BoardType.AI: ("ai", "🤖 AI 动态"),
        BoardType.ENGINEERING: ("engineering", "⚙️ 工程技术"),
        BoardType.RESEARCH: ("research", "📚 研究论文"),
        BoardType.GENERAL: ("general", "📰 综合资讯"),
    }

    for bt, (section_id, section_title) in board_labels.items():
        board_topics = await topic_repo.list_by_board(bt, limit=5)
        if board_topics:
            board_topics.sort(key=lambda t: float(t.heat_score), reverse=True)
            section_items = [_topic_to_feed_item(t) for t in board_topics[:5]]
            sections.append(
                FeedSectionView(
                    section_id=section_id,
                    section_title=section_title,
                    items=section_items,
                    show_more_link=f"/feed/{section_id}",
                    display_style="list",
                )
            )

    # If no board-specific sections, create a single "latest" section
    if not sections and all_topics:
        sections.append(
            FeedSectionView(
                section_id="latest",
                section_title="最新动态",
                items=[_topic_to_feed_item(t) for t in all_topics[:max_items]],
                show_more_link="/feed",
                display_style="list",
            )
        )

    # Collect trending tags (placeholder - would come from tag aggregation)
    trending_tags: list[str] = []

    return HomeFeedView(
        sections=sections,
        featured_topic=featured_topic,
        trending_tags=trending_tags,
        last_updated=datetime.now(timezone.utc),
    )


@router.get("/board/{board_type}", response_model=FeedListView)
async def get_board_feed(
    board_type: str,
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    time_window_hours: int = Query(72, ge=1, le=168, description="Time window in hours"),
) -> FeedListView:
    """Get feed for a specific board."""
    valid_boards = ["ai", "engineering", "research", "general"]
    if board_type not in valid_boards:
        return FeedListView(
            items=[],
            total_count=0,
            page=page,
            page_size=page_size,
            has_more=False,
            board_filter=board_type,
            sort_by="heat_score",
            generated_at=datetime.now(timezone.utc),
        )

    topic_repo = TopicRepository(session)
    bt = BoardType(board_type)
    topics = await topic_repo.list_by_board(bt, limit=page_size * 3)
    topics.sort(key=lambda t: float(t.heat_score), reverse=True)

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    page_topics = topics[start:end]

    items = [_topic_to_feed_item(t) for t in page_topics]
    total = len(topics)

    return FeedListView(
        items=items,
        total_count=total,
        page=page,
        page_size=page_size,
        has_more=end < total,
        board_filter=board_type,
        sort_by="heat_score",
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/strategies")
async def list_ranking_strategies() -> dict[str, Any]:
    """List available ranking strategies."""
    return {
        "strategies": [
            {
                "name": "news_ranking",
                "description": "News feed ranking - prioritizes timeliness and source credibility",
                "contexts": ["news_feed", "ai_news", "engineering_news", "research_news"],
            },
            {
                "name": "tech_ranking",
                "description": "Tech feed ranking - prioritizes novelty and trend signals",
                "contexts": ["tech_feed"],
            },
            {
                "name": "homepage_ranking",
                "description": "Homepage ranking - balances importance and board diversity",
                "contexts": ["homepage"],
            },
            {
                "name": "trend_ranking",
                "description": "Trend ranking - prioritizes trend stage and signal strength",
                "contexts": ["trend"],
            },
        ],
    }
