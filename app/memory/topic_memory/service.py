"""Topic Memory Service.

Handles persistence and retrieval of topic memory,
including historian output storage.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import TopicMemoryCreateDTO

if TYPE_CHECKING:
    from app.agents.historian.schemas import HistorianOutput
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class TopicMemoryService:
    """Service for managing topic memory.

    Coordinates:
    - Saving historian output
    - Updating topic memory
    - Managing memory lifecycle
    """

    def __init__(
        self,
        uow: "UnitOfWork | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            uow: Unit of work for database access.
        """
        self._uow = uow

    async def save_historian_output(
        self,
        topic_id: int,
        output: "HistorianOutput",
    ) -> bool:
        """Save historian output to topic memory.

        Args:
            topic_id: ID of the topic.
            output: Historian output to save.

        Returns:
            True if saved successfully.
        """
        if self._uow is None:
            logger.warning("No UoW available, cannot save historian output")
            return False

        try:
            async with self._uow:
                # Check if memory exists
                memory = await self._uow.topic_memories.get_by_topic_id(topic_id)

                now = datetime.now(timezone.utc)

                # Convert output to dict for storage
                output_dict = output.model_dump(mode="json")

                if memory is None:
                    # Create new memory using DTO
                    create_dto = TopicMemoryCreateDTO(
                        topic_id=topic_id,
                        first_seen_at=output.first_seen_at,
                        historical_status=output.historical_status.value,
                        current_stage=output.current_stage.value,
                        history_summary=output.history_summary,
                    )
                    await self._uow.topic_memories.create(create_dto)
                    
                    # Update with additional fields via update method
                    update_data = {
                        "key_milestones_json": [
                            tp.model_dump(mode="json")
                            for tp in output.timeline_points[:10]
                        ],
                        "latest_historian_output_json": output_dict,
                        "historian_confidence": output.historical_confidence,
                        "last_refreshed_at": now,
                    }
                    await self._uow.topic_memories.update(topic_id, update_data)
                    logger.info(f"Created topic memory for topic {topic_id}")
                else:
                    # Update existing memory
                    update_data = {
                        "last_seen_at": output.last_seen_at,
                        "historical_status": output.historical_status.value,
                        "current_stage": output.current_stage.value,
                        "history_summary": output.history_summary,
                        "key_milestones_json": [
                            tp.model_dump(mode="json")
                            for tp in output.timeline_points[:10]
                        ],
                        "latest_historian_output_json": output_dict,
                        "historian_confidence": output.historical_confidence,
                        "last_refreshed_at": now,
                    }
                    await self._uow.topic_memories.update(topic_id, update_data)
                    logger.info(f"Updated topic memory for topic {topic_id}")

                await self._uow.commit()
                return True

        except Exception as e:
            logger.error(f"Error saving historian output for topic {topic_id}: {e}")
            return False

    async def get_historian_output(
        self,
        topic_id: int,
    ) -> dict[str, Any] | None:
        """Get stored historian output for a topic.

        Args:
            topic_id: ID of the topic.

        Returns:
            Historian output dict or None.
        """
        if self._uow is None:
            return None

        try:
            async with self._uow:
                memory = await self._uow.topic_memories.get_by_topic_id(topic_id)
                if memory is None:
                    return None
                # Access the raw model to get historian output
                # The DTO doesn't include this field, so we need to query directly
                return getattr(memory, "latest_historian_output_json", None)

        except Exception as e:
            logger.error(f"Error getting historian output for topic {topic_id}: {e}")
            return None

    async def update_from_historian(
        self,
        topic_id: int,
        output: "HistorianOutput",
    ) -> bool:
        """Update topic memory from historian output.

        This is the main entry point for persisting historian results.

        Args:
            topic_id: ID of the topic.
            output: Historian output.

        Returns:
            True if updated successfully.
        """
        # Save the historian output
        saved = await self.save_historian_output(topic_id, output)

        if saved:
            # Optionally create a judgement log
            await self._create_historian_judgement(topic_id, output)

        return saved

    async def _create_historian_judgement(
        self,
        topic_id: int,
        output: "HistorianOutput",
    ) -> None:
        """Create a judgement log entry for historian analysis.

        Args:
            topic_id: ID of the topic.
            output: Historian output.
        """
        if self._uow is None:
            return

        try:
            async with self._uow:
                from app.contracts.dto.memory import JudgementCreateDTO
                
                # Build evidence list from output
                evidence = []
                if output.history_summary:
                    evidence.append(f"History: {output.history_summary[:200]}")
                if output.what_is_new_this_time:
                    evidence.append(f"New: {output.what_is_new_this_time[:200]}")
                evidence.append(f"Timeline events: {len(output.timeline_points)}")
                evidence.append(f"Similar topics: {len(output.similar_past_topics)}")
                
                judgement_dto = JudgementCreateDTO(
                    target_type="topic",
                    target_id=topic_id,
                    agent_name="historian",
                    judgement_type="historical_analysis",
                    judgement=f"Status: {output.historical_status.value}, Stage: {output.current_stage.value}",
                    confidence=output.historical_confidence,
                    evidence=evidence,
                )
                await self._uow.judgements.create_log(judgement_dto)
                await self._uow.commit()
                logger.debug(f"Created historian judgement for topic {topic_id}")

        except Exception as e:
            logger.warning(f"Failed to create historian judgement: {e}")
