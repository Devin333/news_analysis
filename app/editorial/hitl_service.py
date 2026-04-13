"""Human-in-the-loop service for editorial operations."""

from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.editorial import (
    AgentType,
    ArchiveContentDTO,
    EditorActionDTO,
    EditorActionResultDTO,
    EditorActionStatus,
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

if TYPE_CHECKING:
    from app.storage.repositories.editor_action_repository import EditorActionRepository
    from app.storage.repositories.topic_copy_repository import TopicCopyRepository
    from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)


class HITLService:
    """Human-in-the-loop service for editorial operations.

    Handles:
    - Approving/rejecting content
    - Revising copy
    - Reassigning boards
    - Splitting/merging topics
    - Requesting agent reruns
    - Pinning/featuring content
    - Archiving content
    """

    def __init__(
        self,
        action_repo: "EditorActionRepository | None" = None,
        topic_repo: "TopicRepository | None" = None,
        copy_repo: "TopicCopyRepository | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            action_repo: Editor action repository.
            topic_repo: Topic repository.
            copy_repo: Topic copy repository.
        """
        self._action_repo = action_repo
        self._topic_repo = topic_repo
        self._copy_repo = copy_repo

    async def approve_copy(
        self,
        copy_id: int,
        editor_key: str,
        *,
        reason: str | None = None,
        notes: str | None = None,
    ) -> EditorActionResultDTO:
        """Approve a copy.

        Args:
            copy_id: Copy ID.
            editor_key: Editor identifier.
            reason: Reason for approval.
            notes: Additional notes.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            # Record the action
            action = await self._action_repo.create(
                target_type=TargetType.COPY.value,
                target_id=copy_id,
                action_type=EditorActionType.APPROVE.value,
                editor_key=editor_key,
                reason=reason,
                notes=notes,
            )

            # Update copy status if repository available
            if self._copy_repo:
                await self._copy_repo.update_review_status(copy_id, "approved")

            logger.info(f"Copy {copy_id} approved by {editor_key}")

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"Copy {copy_id} approved",
                affected_ids=[copy_id],
                changes={"status": "approved"},
            )

        except Exception as e:
            logger.error(f"Failed to approve copy {copy_id}: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def reject_copy(
        self,
        data: RejectActionDTO,
    ) -> EditorActionResultDTO:
        """Reject a copy.

        Args:
            data: Reject action data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=data.target_type.value,
                target_id=data.target_id,
                action_type=EditorActionType.REJECT.value,
                editor_key=data.editor_key,
                reason=data.reason,
                notes=data.notes,
                action_payload={"suggest_revision": data.suggest_revision},
            )

            # Update copy status if repository available
            if self._copy_repo and data.target_type == TargetType.COPY:
                await self._copy_repo.update_review_status(data.target_id, "rejected")

            logger.info(f"{data.target_type} {data.target_id} rejected by {data.editor_key}")

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"{data.target_type} {data.target_id} rejected",
                affected_ids=[data.target_id],
                changes={"status": "rejected"},
            )

        except Exception as e:
            logger.error(f"Failed to reject {data.target_type} {data.target_id}: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def revise_copy(
        self,
        data: ReviseCopyDTO,
    ) -> EditorActionResultDTO:
        """Revise a copy.

        Args:
            data: Revise copy data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            changes: dict[str, Any] = {}
            if data.new_title:
                changes["title"] = data.new_title
            if data.new_summary:
                changes["summary"] = data.new_summary
            if data.new_body:
                changes["body"] = data.new_body

            action = await self._action_repo.create(
                target_type=TargetType.COPY.value,
                target_id=data.copy_id,
                action_type=EditorActionType.REVISE_COPY.value,
                editor_key=data.editor_key,
                reason=data.reason,
                action_payload=changes,
            )

            # Update copy if repository available
            if self._copy_repo and changes:
                await self._copy_repo.update_content(
                    data.copy_id,
                    title=data.new_title,
                    summary=data.new_summary,
                    body=data.new_body,
                )

            logger.info(f"Copy {data.copy_id} revised by {data.editor_key}")

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"Copy {data.copy_id} revised",
                affected_ids=[data.copy_id],
                changes=changes,
            )

        except Exception as e:
            logger.error(f"Failed to revise copy {data.copy_id}: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def override_topic_board(
        self,
        data: ReassignBoardDTO,
    ) -> EditorActionResultDTO:
        """Override topic board assignment.

        Args:
            data: Reassign board data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=TargetType.TOPIC.value,
                target_id=data.topic_id,
                action_type=EditorActionType.REASSIGN_BOARD.value,
                editor_key=data.editor_key,
                reason=data.reason,
                action_payload={"new_board_type": data.new_board_type},
            )

            # Update topic if repository available
            if self._topic_repo:
                await self._topic_repo.update_board_type(
                    data.topic_id, data.new_board_type
                )

            logger.info(
                f"Topic {data.topic_id} board changed to {data.new_board_type} "
                f"by {data.editor_key}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"Topic {data.topic_id} board changed to {data.new_board_type}",
                affected_ids=[data.topic_id],
                changes={"board_type": data.new_board_type},
            )

        except Exception as e:
            logger.error(f"Failed to reassign board for topic {data.topic_id}: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def request_rerun_agent(
        self,
        data: RerunAgentDTO,
    ) -> EditorActionResultDTO:
        """Request agent rerun for a target.

        Args:
            data: Rerun agent data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=data.target_type.value,
                target_id=data.target_id,
                action_type=EditorActionType.RERUN_AGENT.value,
                editor_key=data.editor_key,
                reason=data.reason,
                action_payload={
                    "agent_type": data.agent_type.value,
                    "force": data.force,
                },
                status="pending",  # Will be completed when agent runs
            )

            logger.info(
                f"Agent rerun requested: {data.agent_type} for "
                f"{data.target_type} {data.target_id} by {data.editor_key}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"Agent rerun requested: {data.agent_type}",
                affected_ids=[data.target_id],
                changes={"rerun_requested": data.agent_type.value},
            )

        except Exception as e:
            logger.error(f"Failed to request agent rerun: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def merge_topics_manual(
        self,
        data: MergeTopicsDTO,
    ) -> EditorActionResultDTO:
        """Manually merge topics.

        Args:
            data: Merge topics data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=TargetType.TOPIC.value,
                target_id=data.target_topic_id,
                action_type=EditorActionType.MERGE_TOPIC.value,
                editor_key=data.editor_key,
                reason=data.reason,
                action_payload={
                    "source_topic_ids": data.source_topic_ids,
                    "target_topic_id": data.target_topic_id,
                },
            )

            # Perform merge if repository available
            merged_ids = []
            if self._topic_repo:
                for source_id in data.source_topic_ids:
                    if source_id != data.target_topic_id:
                        # Move items from source to target
                        await self._topic_repo.merge_into(
                            source_id, data.target_topic_id
                        )
                        merged_ids.append(source_id)

            logger.info(
                f"Topics {data.source_topic_ids} merged into {data.target_topic_id} "
                f"by {data.editor_key}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"Topics merged into {data.target_topic_id}",
                affected_ids=[data.target_topic_id] + merged_ids,
                changes={"merged_from": data.source_topic_ids},
            )

        except Exception as e:
            logger.error(f"Failed to merge topics: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def split_topic_manual(
        self,
        data: SplitTopicDTO,
    ) -> EditorActionResultDTO:
        """Manually split a topic.

        Args:
            data: Split topic data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=TargetType.TOPIC.value,
                target_id=data.topic_id,
                action_type=EditorActionType.SPLIT_TOPIC.value,
                editor_key=data.editor_key,
                reason=data.reason,
                action_payload={
                    "split_item_ids": data.split_item_ids,
                    "new_topic_title": data.new_topic_title,
                },
            )

            new_topic_id = None
            if self._topic_repo and data.split_item_ids:
                # Create new topic and move items
                new_topic_id = await self._topic_repo.split_items(
                    data.topic_id,
                    data.split_item_ids,
                    new_title=data.new_topic_title,
                )

            logger.info(
                f"Topic {data.topic_id} split by {data.editor_key}, "
                f"new topic: {new_topic_id}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"Topic split, new topic ID: {new_topic_id}",
                affected_ids=[data.topic_id] + ([new_topic_id] if new_topic_id else []),
                changes={
                    "split_items": data.split_item_ids,
                    "new_topic_id": new_topic_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to split topic {data.topic_id}: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def pin_content(
        self,
        data: PinContentDTO,
    ) -> EditorActionResultDTO:
        """Pin content.

        Args:
            data: Pin content data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=data.target_type.value,
                target_id=data.target_id,
                action_type=EditorActionType.PIN.value,
                editor_key=data.editor_key,
                reason=data.reason,
                action_payload={
                    "pin_position": data.pin_position,
                    "pin_until": data.pin_until.isoformat() if data.pin_until else None,
                },
            )

            logger.info(
                f"{data.target_type} {data.target_id} pinned by {data.editor_key}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"{data.target_type} {data.target_id} pinned",
                affected_ids=[data.target_id],
                changes={"pinned": True, "pin_position": data.pin_position},
            )

        except Exception as e:
            logger.error(f"Failed to pin content: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def unpin_content(
        self,
        target_type: TargetType,
        target_id: int,
        editor_key: str,
        *,
        reason: str | None = None,
    ) -> EditorActionResultDTO:
        """Unpin content.

        Args:
            target_type: Type of target.
            target_id: Target ID.
            editor_key: Editor identifier.
            reason: Reason for unpinning.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=target_type.value,
                target_id=target_id,
                action_type=EditorActionType.UNPIN.value,
                editor_key=editor_key,
                reason=reason,
            )

            logger.info(f"{target_type} {target_id} unpinned by {editor_key}")

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"{target_type} {target_id} unpinned",
                affected_ids=[target_id],
                changes={"pinned": False},
            )

        except Exception as e:
            logger.error(f"Failed to unpin content: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def feature_content(
        self,
        data: FeatureContentDTO,
    ) -> EditorActionResultDTO:
        """Feature content.

        Args:
            data: Feature content data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=data.target_type.value,
                target_id=data.target_id,
                action_type=EditorActionType.FEATURE.value,
                editor_key=data.editor_key,
                reason=data.reason,
                action_payload={
                    "feature_section": data.feature_section,
                    "feature_until": data.feature_until.isoformat() if data.feature_until else None,
                },
            )

            logger.info(
                f"{data.target_type} {data.target_id} featured by {data.editor_key}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"{data.target_type} {data.target_id} featured",
                affected_ids=[data.target_id],
                changes={"featured": True, "feature_section": data.feature_section},
            )

        except Exception as e:
            logger.error(f"Failed to feature content: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def archive_content(
        self,
        data: ArchiveContentDTO,
    ) -> EditorActionResultDTO:
        """Archive content.

        Args:
            data: Archive content data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=data.target_type.value,
                target_id=data.target_id,
                action_type=EditorActionType.ARCHIVE.value,
                editor_key=data.editor_key,
                reason=data.reason,
            )

            logger.info(
                f"{data.target_type} {data.target_id} archived by {data.editor_key}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"{data.target_type} {data.target_id} archived",
                affected_ids=[data.target_id],
                changes={"archived": True},
            )

        except Exception as e:
            logger.error(f"Failed to archive content: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def restore_content(
        self,
        data: ArchiveContentDTO,
    ) -> EditorActionResultDTO:
        """Restore archived content.

        Args:
            data: Restore content data.

        Returns:
            Action result.
        """
        if not self._action_repo:
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message="Action repository not configured",
            )

        try:
            action = await self._action_repo.create(
                target_type=data.target_type.value,
                target_id=data.target_id,
                action_type=EditorActionType.RESTORE.value,
                editor_key=data.editor_key,
                reason=data.reason,
            )

            logger.info(
                f"{data.target_type} {data.target_id} restored by {data.editor_key}"
            )

            return EditorActionResultDTO(
                action_id=action.id,
                success=True,
                message=f"{data.target_type} {data.target_id} restored",
                affected_ids=[data.target_id],
                changes={"archived": False},
            )

        except Exception as e:
            logger.error(f"Failed to restore content: {e}")
            return EditorActionResultDTO(
                action_id=0,
                success=False,
                message=str(e),
            )

    async def get_action_history(
        self,
        target_type: TargetType,
        target_id: int,
        *,
        limit: int = 50,
    ) -> list[EditorActionDTO]:
        """Get action history for a target.

        Args:
            target_type: Type of target.
            target_id: Target ID.
            limit: Maximum actions.

        Returns:
            List of actions.
        """
        if not self._action_repo:
            return []

        actions = await self._action_repo.list_by_target(
            target_type.value, target_id, limit=limit
        )

        return [
            EditorActionDTO(
                id=a.id,
                target_type=TargetType(a.target_type),
                target_id=a.target_id,
                action_type=EditorActionType(a.action_type),
                action_payload=a.action_payload_json or {},
                editor_key=a.editor_key,
                reason=a.reason,
                notes=a.notes,
                status=EditorActionStatus(a.status),
                error_message=a.error_message,
                parent_action_id=a.parent_action_id,
                created_at=a.created_at,
            )
            for a in actions
        ]

    async def get_pending_reruns(
        self,
        agent_type: AgentType | None = None,
    ) -> list[EditorActionDTO]:
        """Get pending agent rerun requests.

        Args:
            agent_type: Optional agent type filter.

        Returns:
            List of pending rerun actions.
        """
        if not self._action_repo:
            return []

        actions = await self._action_repo.list_by_action_type(
            EditorActionType.RERUN_AGENT.value,
            limit=100,
        )

        # Filter for pending status
        pending = [a for a in actions if a.status == "pending"]

        # Filter by agent type if specified
        if agent_type:
            pending = [
                a for a in pending
                if a.action_payload_json
                and a.action_payload_json.get("agent_type") == agent_type.value
            ]

        return [
            EditorActionDTO(
                id=a.id,
                target_type=TargetType(a.target_type),
                target_id=a.target_id,
                action_type=EditorActionType(a.action_type),
                action_payload=a.action_payload_json or {},
                editor_key=a.editor_key,
                reason=a.reason,
                notes=a.notes,
                status=EditorActionStatus(a.status),
                error_message=a.error_message,
                parent_action_id=a.parent_action_id,
                created_at=a.created_at,
            )
            for a in pending
        ]

    async def complete_rerun(
        self,
        action_id: int,
        *,
        success: bool = True,
        error_message: str | None = None,
    ) -> bool:
        """Mark a rerun request as completed.

        Args:
            action_id: Action ID.
            success: Whether rerun succeeded.
            error_message: Error message if failed.

        Returns:
            True if updated.
        """
        if not self._action_repo:
            return False

        status = "completed" if success else "failed"
        return await self._action_repo.update_status(
            action_id, status, error_message=error_message
        )
