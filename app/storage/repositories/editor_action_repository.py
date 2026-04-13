"""Editor action repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.storage.db.models.editor_action import EditorAction

logger = get_logger(__name__)


class EditorActionRepository:
    """Repository for editor action operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create(
        self,
        target_type: str,
        target_id: int,
        action_type: str,
        editor_key: str,
        *,
        action_payload: dict[str, Any] | None = None,
        reason: str | None = None,
        notes: str | None = None,
        status: str = "completed",
        parent_action_id: int | None = None,
    ) -> EditorAction:
        """Create an editor action.

        Args:
            target_type: Type of target.
            target_id: ID of target.
            action_type: Type of action.
            editor_key: Editor identifier.
            action_payload: Action-specific payload.
            reason: Reason for action.
            notes: Additional notes.
            status: Action status.
            parent_action_id: Parent action ID for reverts.

        Returns:
            Created EditorAction.
        """
        model = EditorAction(
            target_type=target_type,
            target_id=target_id,
            action_type=action_type,
            editor_key=editor_key,
            action_payload_json=action_payload,
            reason=reason,
            notes=notes,
            status=status,
            parent_action_id=parent_action_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(
            f"Created editor action {model.id}: "
            f"{action_type} on {target_type}:{target_id} by {editor_key}"
        )
        return model

    async def get_by_id(self, action_id: int) -> EditorAction | None:
        """Get action by ID.

        Args:
            action_id: Action ID.

        Returns:
            EditorAction or None.
        """
        stmt = select(EditorAction).where(EditorAction.id == action_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_target(
        self,
        target_type: str,
        target_id: int,
        *,
        limit: int = 50,
    ) -> list[EditorAction]:
        """List actions for a target.

        Args:
            target_type: Type of target.
            target_id: ID of target.
            limit: Maximum actions.

        Returns:
            List of EditorAction.
        """
        stmt = (
            select(EditorAction)
            .where(
                EditorAction.target_type == target_type,
                EditorAction.target_id == target_id,
            )
            .order_by(EditorAction.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_editor(
        self,
        editor_key: str,
        *,
        action_type: str | None = None,
        limit: int = 50,
    ) -> list[EditorAction]:
        """List actions by an editor.

        Args:
            editor_key: Editor identifier.
            action_type: Optional action type filter.
            limit: Maximum actions.

        Returns:
            List of EditorAction.
        """
        stmt = select(EditorAction).where(EditorAction.editor_key == editor_key)

        if action_type:
            stmt = stmt.where(EditorAction.action_type == action_type)

        stmt = stmt.order_by(EditorAction.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_action_type(
        self,
        action_type: str,
        *,
        target_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[EditorAction]:
        """List actions by type.

        Args:
            action_type: Action type.
            target_type: Optional target type filter.
            since: Optional datetime filter.
            limit: Maximum actions.

        Returns:
            List of EditorAction.
        """
        stmt = select(EditorAction).where(EditorAction.action_type == action_type)

        if target_type:
            stmt = stmt.where(EditorAction.target_type == target_type)

        if since:
            stmt = stmt.where(EditorAction.created_at >= since)

        stmt = stmt.order_by(EditorAction.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> list[EditorAction]:
        """List recent actions.

        Args:
            limit: Maximum actions.
            status: Optional status filter.

        Returns:
            List of EditorAction.
        """
        stmt = select(EditorAction)

        if status:
            stmt = stmt.where(EditorAction.status == status)

        stmt = stmt.order_by(EditorAction.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        action_id: int,
        status: str,
        *,
        error_message: str | None = None,
    ) -> bool:
        """Update action status.

        Args:
            action_id: Action ID.
            status: New status.
            error_message: Optional error message.

        Returns:
            True if updated.
        """
        values: dict[str, Any] = {"status": status}
        if error_message:
            values["error_message"] = error_message

        stmt = (
            update(EditorAction)
            .where(EditorAction.id == action_id)
            .values(**values)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def count_by_target(
        self,
        target_type: str,
        target_id: int,
    ) -> int:
        """Count actions for a target.

        Args:
            target_type: Type of target.
            target_id: ID of target.

        Returns:
            Count of actions.
        """
        stmt = (
            select(func.count())
            .select_from(EditorAction)
            .where(
                EditorAction.target_type == target_type,
                EditorAction.target_id == target_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_by_editor(
        self,
        editor_key: str,
        *,
        since: datetime | None = None,
    ) -> int:
        """Count actions by an editor.

        Args:
            editor_key: Editor identifier.
            since: Optional datetime filter.

        Returns:
            Count of actions.
        """
        stmt = (
            select(func.count())
            .select_from(EditorAction)
            .where(EditorAction.editor_key == editor_key)
        )

        if since:
            stmt = stmt.where(EditorAction.created_at >= since)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_last_action_for_target(
        self,
        target_type: str,
        target_id: int,
        action_type: str | None = None,
    ) -> EditorAction | None:
        """Get the last action for a target.

        Args:
            target_type: Type of target.
            target_id: ID of target.
            action_type: Optional action type filter.

        Returns:
            Last EditorAction or None.
        """
        stmt = select(EditorAction).where(
            EditorAction.target_type == target_type,
            EditorAction.target_id == target_id,
        )

        if action_type:
            stmt = stmt.where(EditorAction.action_type == action_type)

        stmt = stmt.order_by(EditorAction.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_action(
        self,
        target_type: str,
        target_id: int,
        action_type: str,
    ) -> bool:
        """Check if target has a specific action.

        Args:
            target_type: Type of target.
            target_id: ID of target.
            action_type: Action type to check.

        Returns:
            True if action exists.
        """
        stmt = (
            select(func.count())
            .select_from(EditorAction)
            .where(
                EditorAction.target_type == target_type,
                EditorAction.target_id == target_id,
                EditorAction.action_type == action_type,
                EditorAction.status == "completed",
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0
