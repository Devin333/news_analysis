"""Admin API router.

Provides endpoints for operational debugging and management.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.bootstrap.logging import get_logger
from app.contracts.dto.editorial import (
    AgentType,
    ArchiveContentDTO,
    EditorActionType,
    FeatureContentDTO,
    MergeTopicsDTO,
    PinContentDTO,
    ReassignBoardDTO,
    RejectActionDTO,
    RerunAgentDTO,
    ReviseCopyDTO,
    SplitTopicDTO,
    TargetType,
)
from app.editorial.hitl_service import HITLService
from app.storage.repositories.editor_action_repository import EditorActionRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# Request schemas
class ApproveRequest(BaseModel):
    """Request to approve content."""
    editor_key: str
    reason: str | None = None
    notes: str | None = None


class RejectRequest(BaseModel):
    """Request to reject content."""
    editor_key: str
    reason: str
    notes: str | None = None
    suggest_revision: bool = False


class ReviseCopyRequest(BaseModel):
    """Request to revise copy."""
    editor_key: str
    new_title: str | None = None
    new_summary: str | None = None
    new_body: str | None = None
    reason: str | None = None


class ReassignBoardRequest(BaseModel):
    """Request to reassign board."""
    editor_key: str
    new_board_type: str
    reason: str | None = None


class RerunAgentRequest(BaseModel):
    """Request to rerun agent."""
    editor_key: str
    agent_type: str
    reason: str | None = None
    force: bool = False


class MergeTopicsRequest(BaseModel):
    """Request to merge topics."""
    editor_key: str
    source_topic_ids: list[int]
    reason: str | None = None


class SplitTopicRequest(BaseModel):
    """Request to split topic."""
    editor_key: str
    split_item_ids: list[int]
    new_topic_title: str | None = None
    reason: str | None = None


def _get_hitl_service(session: AsyncSession) -> HITLService:
    """Create HITL service with dependencies."""
    action_repo = EditorActionRepository(session)
    return HITLService(action_repo=action_repo)


# ============== HITL Copy Operations ==============

@router.post("/copies/{copy_id}/approve")
async def approve_copy(
    copy_id: int,
    request: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Approve a copy.

    Args:
        copy_id: Copy ID.
        request: Approve request.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.approve_copy(
        copy_id=copy_id,
        editor_key=request.editor_key,
        reason=request.reason,
        notes=request.notes,
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


@router.post("/copies/{copy_id}/reject")
async def reject_copy(
    copy_id: int,
    request: RejectRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reject a copy.

    Args:
        copy_id: Copy ID.
        request: Reject request.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.reject_copy(
        RejectActionDTO(
            target_type=TargetType.COPY,
            target_id=copy_id,
            editor_key=request.editor_key,
            reason=request.reason,
            notes=request.notes,
            suggest_revision=request.suggest_revision,
        )
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


@router.post("/copies/{copy_id}/revise")
async def revise_copy(
    copy_id: int,
    request: ReviseCopyRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Revise a copy.

    Args:
        copy_id: Copy ID.
        request: Revise request.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.revise_copy(
        ReviseCopyDTO(
            copy_id=copy_id,
            editor_key=request.editor_key,
            new_title=request.new_title,
            new_summary=request.new_summary,
            new_body=request.new_body,
            reason=request.reason,
        )
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


# ============== HITL Topic Operations ==============

@router.post("/topics/{topic_id}/reassign-board")
async def reassign_topic_board(
    topic_id: int,
    request: ReassignBoardRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Reassign topic board.

    Args:
        topic_id: Topic ID.
        request: Reassign request.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.override_topic_board(
        ReassignBoardDTO(
            topic_id=topic_id,
            editor_key=request.editor_key,
            new_board_type=request.new_board_type,
            reason=request.reason,
        )
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


@router.post("/topics/{topic_id}/rerun-historian")
async def rerun_historian(
    topic_id: int,
    request: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Request historian rerun for topic.

    Args:
        topic_id: Topic ID.
        request: Request with editor key.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.request_rerun_agent(
        RerunAgentDTO(
            target_type=TargetType.TOPIC,
            target_id=topic_id,
            agent_type=AgentType.HISTORIAN,
            editor_key=request.editor_key,
            reason=request.reason,
        )
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


@router.post("/topics/{topic_id}/rerun-analyst")
async def rerun_analyst(
    topic_id: int,
    request: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Request analyst rerun for topic.

    Args:
        topic_id: Topic ID.
        request: Request with editor key.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.request_rerun_agent(
        RerunAgentDTO(
            target_type=TargetType.TOPIC,
            target_id=topic_id,
            agent_type=AgentType.ANALYST,
            editor_key=request.editor_key,
            reason=request.reason,
        )
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


@router.post("/topics/{topic_id}/merge")
async def merge_topics(
    topic_id: int,
    request: MergeTopicsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Merge topics into target topic.

    Args:
        topic_id: Target topic ID.
        request: Merge request.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.merge_topics_manual(
        MergeTopicsDTO(
            source_topic_ids=request.source_topic_ids,
            target_topic_id=topic_id,
            editor_key=request.editor_key,
            reason=request.reason,
        )
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


@router.post("/topics/{topic_id}/split")
async def split_topic(
    topic_id: int,
    request: SplitTopicRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Split topic.

    Args:
        topic_id: Topic ID.
        request: Split request.
        session: Database session.

    Returns:
        Action result.
    """
    service = _get_hitl_service(session)
    result = await service.split_topic_manual(
        SplitTopicDTO(
            topic_id=topic_id,
            editor_key=request.editor_key,
            split_item_ids=request.split_item_ids,
            new_topic_title=request.new_topic_title,
            reason=request.reason,
        )
    )
    return {
        "action_id": result.action_id,
        "success": result.success,
        "message": result.message,
        "affected_ids": result.affected_ids,
        "changes": result.changes,
    }


# ============== HITL Action History ==============

@router.get("/actions")
async def list_editor_actions(
    editor_key: str | None = Query(None),
    action_type: str | None = Query(None),
    target_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List editor actions.

    Args:
        editor_key: Optional filter by editor.
        action_type: Optional filter by action type.
        target_type: Optional filter by target type.
        limit: Maximum actions.
        session: Database session.

    Returns:
        List of actions.
    """
    action_repo = EditorActionRepository(session)

    if editor_key:
        actions = await action_repo.list_by_editor(
            editor_key, action_type=action_type, limit=limit
        )
    elif action_type:
        actions = await action_repo.list_by_action_type(
            action_type, target_type=target_type, limit=limit
        )
    else:
        actions = await action_repo.list_recent(limit=limit)

    return {
        "actions": [
            {
                "id": a.id,
                "target_type": a.target_type,
                "target_id": a.target_id,
                "action_type": a.action_type,
                "editor_key": a.editor_key,
                "reason": a.reason,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ],
        "total": len(actions),
        "filters": {
            "editor_key": editor_key,
            "action_type": action_type,
            "target_type": target_type,
        },
    }


@router.get("/actions/{action_id}")
async def get_editor_action(
    action_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get editor action details.

    Args:
        action_id: Action ID.
        session: Database session.

    Returns:
        Action details.
    """
    action_repo = EditorActionRepository(session)
    action = await action_repo.get_by_id(action_id)

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    return {
        "id": action.id,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "action_type": action.action_type,
        "action_payload": action.action_payload_json,
        "editor_key": action.editor_key,
        "reason": action.reason,
        "notes": action.notes,
        "status": action.status,
        "error_message": action.error_message,
        "parent_action_id": action.parent_action_id,
        "created_at": action.created_at.isoformat(),
    }


@router.get("/actions/target/{target_type}/{target_id}")
async def get_target_action_history(
    target_type: str,
    target_id: int,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get action history for a target.

    Args:
        target_type: Target type.
        target_id: Target ID.
        limit: Maximum actions.
        session: Database session.

    Returns:
        Action history.
    """
    action_repo = EditorActionRepository(session)
    actions = await action_repo.list_by_target(target_type, target_id, limit=limit)

    return {
        "target_type": target_type,
        "target_id": target_id,
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "editor_key": a.editor_key,
                "reason": a.reason,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ],
        "total": len(actions),
    }


@router.get("/pending-reruns")
async def get_pending_reruns(
    agent_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get pending agent rerun requests.

    Args:
        agent_type: Optional filter by agent type.
        session: Database session.

    Returns:
        List of pending reruns.
    """
    service = _get_hitl_service(session)
    agent = AgentType(agent_type) if agent_type else None
    pending = await service.get_pending_reruns(agent)

    return {
        "pending_reruns": [
            {
                "action_id": p.id,
                "target_type": p.target_type.value,
                "target_id": p.target_id,
                "agent_type": p.action_payload.get("agent_type"),
                "editor_key": p.editor_key,
                "reason": p.reason,
                "created_at": p.created_at.isoformat(),
            }
            for p in pending
        ],
        "total": len(pending),
        "filter": {"agent_type": agent_type},
    }


# ============== Agent Runs ==============

@router.get("/agent-runs")
async def list_agent_runs(
    agent_name: str | None = Query(default=None, description="Filter by agent name"),
    topic_id: int | None = Query(default=None, description="Filter by topic ID"),
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List agent run logs.

    Args:
        agent_name: Optional filter by agent.
        topic_id: Optional filter by topic.
        status: Optional filter by status.
        limit: Maximum runs to return.

    Returns:
        List of agent runs.
    """
    return {
        "runs": [],
        "total": 0,
        "filters": {
            "agent_name": agent_name,
            "topic_id": topic_id,
            "status": status,
        },
    }


@router.get("/agent-runs/{run_id}")
async def get_agent_run(
    run_id: str,
) -> dict[str, Any]:
    """Get details of a specific agent run.

    Args:
        run_id: Agent run ID.

    Returns:
        Agent run details.
    """
    return {
        "run_id": run_id,
        "status": "not_found",
        "message": "Agent run not found",
    }


# ============== Reviews ==============

@router.get("/reviews")
async def list_reviews(
    target_type: str | None = Query(default=None, description="Filter by target type"),
    review_status: str | None = Query(default=None, description="Filter by review status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List review logs.

    Args:
        target_type: Optional filter by target type.
        review_status: Optional filter by status.
        limit: Maximum reviews to return.

    Returns:
        List of reviews.
    """
    return {
        "reviews": [],
        "total": 0,
        "filters": {
            "target_type": target_type,
            "review_status": review_status,
        },
    }


@router.get("/reviews/{review_id}")
async def get_review(
    review_id: int,
) -> dict[str, Any]:
    """Get review details.

    Args:
        review_id: Review ID.

    Returns:
        Review details.
    """
    return {
        "id": review_id,
        "status": "not_found",
    }


# ============== Copies ==============

@router.get("/copies")
async def list_copies(
    copy_type: str | None = Query(default=None, description="Filter by copy type"),
    status: str | None = Query(default=None, description="Filter by status"),
    topic_id: int | None = Query(default=None, description="Filter by topic ID"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List topic copies.

    Args:
        copy_type: Optional filter by type.
        status: Optional filter by status.
        topic_id: Optional filter by topic.
        limit: Maximum copies to return.

    Returns:
        List of copies.
    """
    return {
        "copies": [],
        "total": 0,
        "filters": {
            "copy_type": copy_type,
            "status": status,
            "topic_id": topic_id,
        },
    }


@router.get("/copies/{copy_id}")
async def get_copy(
    copy_id: int,
) -> dict[str, Any]:
    """Get copy details.

    Args:
        copy_id: Copy ID.

    Returns:
        Copy details.
    """
    return {
        "id": copy_id,
        "status": "not_found",
    }


@router.get("/copies/{copy_id}/review-status")
async def get_copy_review_status(
    copy_id: int,
) -> dict[str, Any]:
    """Get review status for a copy.

    Args:
        copy_id: Copy ID.

    Returns:
        Review status.
    """
    return {
        "copy_id": copy_id,
        "review_status": None,
        "reviews": [],
    }


# ============== Topics Debug ==============

@router.get("/topics/{topic_id}/debug")
async def debug_topic(
    topic_id: int,
) -> dict[str, Any]:
    """Get debug information for a topic.

    Includes:
    - Topic metadata
    - Historical snapshots
    - Writer/Reviewer results
    - Agent run history

    Args:
        topic_id: Topic ID.

    Returns:
        Debug information.
    """
    return {
        "topic_id": topic_id,
        "topic": None,
        "snapshots": [],
        "copies": [],
        "reviews": [],
        "agent_runs": [],
        "timeline_events": [],
        "insights": None,
    }


@router.get("/topics/{topic_id}/reviews")
async def get_topic_reviews(
    topic_id: int,
) -> dict[str, Any]:
    """Get all reviews for a topic.

    Args:
        topic_id: Topic ID.

    Returns:
        List of reviews.
    """
    return {
        "topic_id": topic_id,
        "reviews": [],
        "total": 0,
    }


@router.get("/topics/{topic_id}/snapshots")
async def get_topic_snapshots(
    topic_id: int,
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """Get historical snapshots for a topic.

    Args:
        topic_id: Topic ID.
        limit: Maximum snapshots.

    Returns:
        List of snapshots.
    """
    return {
        "topic_id": topic_id,
        "snapshots": [],
        "total": 0,
    }


@router.post("/topics/{topic_id}/rebuild")
async def rebuild_topic_intelligence(
    topic_id: int,
    run_historian: bool = Query(default=True),
    run_analyst: bool = Query(default=True),
    run_writer: bool = Query(default=True),
    run_reviewer: bool = Query(default=True),
) -> dict[str, Any]:
    """Trigger rebuild of topic intelligence.

    Args:
        topic_id: Topic ID.
        run_historian: Whether to run historian.
        run_analyst: Whether to run analyst.
        run_writer: Whether to run writer.
        run_reviewer: Whether to run reviewer.

    Returns:
        Rebuild status.
    """
    return {
        "status": "queued",
        "topic_id": topic_id,
        "steps": {
            "historian": run_historian,
            "analyst": run_analyst,
            "writer": run_writer,
            "reviewer": run_reviewer,
        },
        "message": "Topic intelligence rebuild queued",
    }


# ============== Trends Debug ==============

@router.get("/trends/debug")
async def debug_trends() -> dict[str, Any]:
    """Get debug information for trend detection.

    Returns:
        Trend detection debug info.
    """
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
        "active_trends": 0,
        "emerging_count": 0,
    }


@router.get("/trends/signals")
async def list_trend_signals(
    topic_id: int | None = Query(default=None),
    signal_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List trend signals.

    Args:
        topic_id: Optional filter by topic.
        signal_type: Optional filter by signal type.
        status: Optional filter by status.
        limit: Maximum signals.

    Returns:
        List of signals.
    """
    return {
        "signals": [],
        "total": 0,
        "filters": {
            "topic_id": topic_id,
            "signal_type": signal_type,
            "status": status,
        },
    }


# ============== Reports Debug ==============

@router.get("/reports/debug")
async def debug_reports() -> dict[str, Any]:
    """Get debug information for report generation.

    Returns:
        Report generation debug info.
    """
    return {
        "status": "ok",
        "report_types": ["daily", "weekly"],
        "statuses": ["draft", "pending_review", "approved", "published", "archived"],
        "total_daily": 0,
        "total_weekly": 0,
        "last_daily_at": None,
        "last_weekly_at": None,
    }


# ============== System Status ==============

@router.get("/status")
async def get_system_status() -> dict[str, Any]:
    """Get overall system status.

    Returns:
        System status information.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": {
            "historian": "available",
            "analyst": "available",
            "writer": "available",
            "reviewer": "available",
            "trend_hunter": "available",
            "report_editor": "available",
        },
        "services": {
            "memory": "available",
            "publish": "available",
            "report": "available",
            "hitl": "available",
        },
    }


@router.get("/stats")
async def get_system_stats() -> dict[str, Any]:
    """Get system statistics.

    Returns:
        System statistics.
    """
    return {
        "topics": {
            "total": 0,
            "with_insights": 0,
            "with_copies": 0,
        },
        "copies": {
            "total": 0,
            "published": 0,
            "pending_review": 0,
        },
        "reviews": {
            "total": 0,
            "approved": 0,
            "rejected": 0,
        },
        "reports": {
            "daily": 0,
            "weekly": 0,
        },
        "trends": {
            "emerging": 0,
            "rising": 0,
            "active": 0,
        },
        "editor_actions": {
            "total": 0,
            "pending_reruns": 0,
        },
    }
