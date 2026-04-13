"""Judgement Repository implementation."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import JudgementCreateDTO, JudgementMemoryDTO
from app.storage.db.models.judgement_log import JudgementLog

logger = get_logger(__name__)


class JudgementRepository:
    """Repository for judgement log operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create_log(self, data: JudgementCreateDTO) -> JudgementMemoryDTO:
        """Create a judgement log.

        Args:
            data: Judgement creation data.

        Returns:
            Created JudgementMemoryDTO.
        """
        model = JudgementLog(
            target_type=data.target_type,
            target_id=data.target_id,
            agent_name=data.agent_name,
            judgement_type=data.judgement_type,
            judgement=data.judgement,
            confidence=data.confidence,
            evidence_json=data.evidence,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(
            f"Created judgement log: {data.judgement_type} for "
            f"{data.target_type}:{data.target_id} by {data.agent_name}"
        )
        return self._to_dto(model)

    async def list_by_target(
        self,
        target_type: str,
        target_id: int,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """List judgements for a target.

        Args:
            target_type: Type of target (topic, entity, item).
            target_id: ID of the target.
            limit: Maximum number of judgements to return.

        Returns:
            List of JudgementMemoryDTO ordered by created_at desc.
        """
        stmt = (
            select(JudgementLog)
            .where(
                JudgementLog.target_type == target_type,
                JudgementLog.target_id == target_id,
            )
            .order_by(JudgementLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._to_dto(row) for row in rows]

    async def list_recent_by_type(
        self,
        judgement_type: str,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """List recent judgements by type.

        Args:
            judgement_type: Type of judgement.
            limit: Maximum number of judgements to return.

        Returns:
            List of JudgementMemoryDTO ordered by created_at desc.
        """
        stmt = (
            select(JudgementLog)
            .where(JudgementLog.judgement_type == judgement_type)
            .order_by(JudgementLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._to_dto(row) for row in rows]

    async def list_by_agent(
        self,
        agent_name: str,
        limit: int = 50,
    ) -> list[JudgementMemoryDTO]:
        """List judgements by agent.

        Args:
            agent_name: Name of the agent.
            limit: Maximum number of judgements to return.

        Returns:
            List of JudgementMemoryDTO.
        """
        stmt = (
            select(JudgementLog)
            .where(JudgementLog.agent_name == agent_name)
            .order_by(JudgementLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._to_dto(row) for row in rows]

    async def find_similar_judgements(
        self,
        judgement: str,
        limit: int = 10,
    ) -> list[JudgementMemoryDTO]:
        """Find similar judgements (stub for future implementation).

        This will be implemented with embedding similarity search.

        Args:
            judgement: Judgement text to find similar ones.
            limit: Maximum number of judgements to return.

        Returns:
            List of similar JudgementMemoryDTO.
        """
        # Stub - will be implemented with vector search
        logger.warning("find_similar_judgements is a stub, returning empty list")
        return []

    async def update_outcome(
        self,
        judgement_id: int,
        outcome: str,
    ) -> JudgementMemoryDTO | None:
        """Update the later outcome of a judgement.

        Args:
            judgement_id: ID of the judgement.
            outcome: The actual outcome for validation.

        Returns:
            Updated JudgementMemoryDTO if found.
        """
        stmt = select(JudgementLog).where(JudgementLog.id == judgement_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        model.later_outcome = outcome
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Updated outcome for judgement {judgement_id}")
        return self._to_dto(model)

    def _to_dto(self, model: JudgementLog) -> JudgementMemoryDTO:
        """Convert ORM model to DTO."""
        return JudgementMemoryDTO(
            id=model.id,
            target_type=model.target_type,
            target_id=model.target_id,
            agent_name=model.agent_name,
            judgement_type=model.judgement_type,
            judgement=model.judgement,
            confidence=model.confidence,
            evidence=model.evidence_json or [],
            created_at=model.created_at,
            later_outcome=model.later_outcome,
            metadata=model.metadata_json or {},
        )
