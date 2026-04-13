"""Judgement Memory Service for managing agent judgements."""

from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import JudgementCreateDTO, JudgementMemoryDTO

if TYPE_CHECKING:
    from app.memory.repositories.judgement_repository import JudgementRepository

logger = get_logger(__name__)


class JudgementMemoryService:
    """Service for managing agent judgement history.

    Provides methods to create, query, and validate judgements
    made by agents over time.
    """

    def __init__(self, repository: "JudgementRepository") -> None:
        """Initialize the service.

        Args:
            repository: Judgement repository.
        """
        self._repo = repository

    async def create_judgement(
        self,
        target_type: str,
        target_id: int,
        agent_name: str,
        judgement_type: str,
        judgement: str,
        confidence: float = 0.0,
        evidence: list[str] | None = None,
    ) -> JudgementMemoryDTO:
        """Create a new judgement record.

        Args:
            target_type: Type of target (topic, entity, item).
            target_id: ID of the target.
            agent_name: Name of the agent making the judgement.
            judgement_type: Type of judgement.
            judgement: The judgement text.
            confidence: Confidence score (0-1).
            evidence: List of evidence supporting the judgement.

        Returns:
            Created JudgementMemoryDTO.
        """
        data = JudgementCreateDTO(
            target_type=target_type,
            target_id=target_id,
            agent_name=agent_name,
            judgement_type=judgement_type,
            judgement=judgement,
            confidence=confidence,
            evidence=evidence or [],
        )
        return await self._repo.create_log(data)

    async def get_judgements_for_topic(
        self,
        topic_id: int,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """Get judgements for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of judgements.

        Returns:
            List of JudgementMemoryDTO.
        """
        return await self._repo.list_by_target("topic", topic_id, limit)

    async def get_judgements_for_entity(
        self,
        entity_id: int,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """Get judgements for an entity.

        Args:
            entity_id: The entity ID.
            limit: Maximum number of judgements.

        Returns:
            List of JudgementMemoryDTO.
        """
        return await self._repo.list_by_target("entity", entity_id, limit)

    async def get_recent_by_type(
        self,
        judgement_type: str,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """Get recent judgements by type.

        Args:
            judgement_type: Type of judgement.
            limit: Maximum number of judgements.

        Returns:
            List of JudgementMemoryDTO.
        """
        return await self._repo.list_recent_by_type(judgement_type, limit)

    async def get_agent_judgements(
        self,
        agent_name: str,
        limit: int = 50,
    ) -> list[JudgementMemoryDTO]:
        """Get judgements made by a specific agent.

        Args:
            agent_name: Name of the agent.
            limit: Maximum number of judgements.

        Returns:
            List of JudgementMemoryDTO.
        """
        return await self._repo.list_by_agent(agent_name, limit)

    async def record_outcome(
        self,
        judgement_id: int,
        outcome: str,
    ) -> JudgementMemoryDTO | None:
        """Record the actual outcome for a judgement.

        Used for validating judgement accuracy over time.

        Args:
            judgement_id: ID of the judgement.
            outcome: The actual outcome.

        Returns:
            Updated JudgementMemoryDTO if found.
        """
        return await self._repo.update_outcome(judgement_id, outcome)

    async def find_similar(
        self,
        judgement: str,
        limit: int = 10,
    ) -> list[JudgementMemoryDTO]:
        """Find similar past judgements.

        Args:
            judgement: Judgement text to find similar ones.
            limit: Maximum number of results.

        Returns:
            List of similar JudgementMemoryDTO.
        """
        return await self._repo.find_similar_judgements(judgement, limit)
