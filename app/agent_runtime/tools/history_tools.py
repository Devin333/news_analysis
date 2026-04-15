"""History tools for Historian Agent.

Provides tools for retrieving historical context, timelines,
snapshots, and related information.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.agent_runtime.tools.base import BaseTool, ToolResult, ToolRegistry
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


# ============ Tool Input Schemas ============


class RetrieveTopicTimelineInput(BaseModel):
    """Input for retrieve_topic_timeline tool."""

    topic_id: int = Field(description="The topic ID to retrieve timeline for")
    limit: int = Field(default=50, description="Maximum number of events to return")


class RetrieveTopicSnapshotsInput(BaseModel):
    """Input for retrieve_topic_snapshots tool."""

    topic_id: int = Field(description="The topic ID to retrieve snapshots for")
    limit: int = Field(default=10, description="Maximum number of snapshots to return")


class RetrieveRelatedTopicsInput(BaseModel):
    """Input for retrieve_related_topics tool."""

    topic_id: int = Field(description="The topic ID to find related topics for")
    limit: int = Field(default=10, description="Maximum number of related topics")


class RetrieveEntityMemoriesInput(BaseModel):
    """Input for retrieve_entity_memories tool."""

    entity_ids: list[int] = Field(description="List of entity IDs to retrieve memories for")


class RetrieveHistoricalJudgementsInput(BaseModel):
    """Input for retrieve_historical_judgements tool."""

    topic_id: int = Field(description="The topic ID to retrieve judgements for")
    judgement_type: str | None = Field(default=None, description="Optional filter by judgement type")
    limit: int = Field(default=20, description="Maximum number of judgements")


# ============ Tool Implementations ============


class RetrieveTopicTimelineTool(BaseTool):
    """Tool to retrieve topic timeline events."""

    name: str = "retrieve_topic_timeline"
    description: str = "Retrieve the timeline of events for a topic, including first seen, releases, papers, and other significant events."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool.

        Args:
            input_data: Tool input containing topic_id and limit.

        Returns:
            ToolResult with timeline events.
        """
        try:
            params = RetrieveTopicTimelineInput(**input_data)

            # Get timeline from retrieval service
            from app.memory.retrieval.service import MemoryRetrievalService

            # This would be injected in real usage
            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            timeline = await retrieval_service.retrieve_topic_timeline(
                params.topic_id,
                limit=params.limit,
            )

            # Convert to serializable format
            events = [
                {
                    "event_time": e.event_time.isoformat(),
                    "event_type": e.event_type,
                    "title": e.title,
                    "description": e.description,
                    "importance_score": e.importance_score,
                    "source_item_id": e.source_item_id,
                }
                for e in timeline
            ]

            return ToolResult.ok({
                    "topic_id": params.topic_id,
                    "event_count": len(events),
                    "events": events,
                },
            )

        except Exception as e:
            logger.error(f"Error retrieving timeline: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        """Get retrieval service from context."""
        # In real usage, this would be injected
        return getattr(self, "_retrieval_service", None)


class RetrieveTopicSnapshotsTool(BaseTool):
    """Tool to retrieve topic snapshots."""

    name: str = "retrieve_topic_snapshots"
    description: str = "Retrieve historical snapshots of a topic, showing how it evolved over time."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = RetrieveTopicSnapshotsInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            snapshots = await retrieval_service.retrieve_topic_snapshots(
                params.topic_id,
                limit=params.limit,
            )

            # Convert to serializable format
            snapshot_data = [
                {
                    "snapshot_at": s.snapshot_at.isoformat(),
                    "summary": s.summary,
                    "why_it_matters": s.why_it_matters,
                    "system_judgement": s.system_judgement,
                    "heat_score": s.heat_score,
                    "item_count": s.item_count,
                    "source_count": s.source_count,
                }
                for s in snapshots
            ]

            return ToolResult.ok({
                    "topic_id": params.topic_id,
                    "snapshot_count": len(snapshot_data),
                    "snapshots": snapshot_data,
                },
            )

        except Exception as e:
            logger.error(f"Error retrieving snapshots: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class RetrieveRelatedTopicsTool(BaseTool):
    """Tool to retrieve related topics."""

    name: str = "retrieve_related_topics"
    description: str = "Find topics that are related to the given topic based on shared entities, tags, or content similarity."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = RetrieveRelatedTopicsInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            related_ids = await retrieval_service.retrieve_related_topics(
                params.topic_id,
                limit=params.limit,
            )

            return ToolResult.ok({
                    "topic_id": params.topic_id,
                    "related_count": len(related_ids),
                    "related_topic_ids": related_ids,
                },
            )

        except Exception as e:
            logger.error(f"Error retrieving related topics: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class RetrieveEntityMemoriesTool(BaseTool):
    """Tool to retrieve entity memories."""

    name: str = "retrieve_entity_memories"
    description: str = "Retrieve historical memories for entities (people, organizations, technologies) mentioned in the topic."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = RetrieveEntityMemoriesInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            memories = []
            for entity_id in params.entity_ids:
                memory = await retrieval_service.retrieve_entity_history(entity_id)
                if memory:
                    memories.append({
                        "entity_id": memory.entity_id,
                        "summary": memory.summary,
                        "related_topic_ids": memory.related_topic_ids,
                        "milestones": memory.milestones,
                    })

            return ToolResult.ok({
                    "entity_count": len(memories),
                    "memories": memories,
                },
            )

        except Exception as e:
            logger.error(f"Error retrieving entity memories: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class RetrieveHistoricalJudgementsTool(BaseTool):
    """Tool to retrieve historical judgements."""

    name: str = "retrieve_historical_judgements"
    description: str = "Retrieve past system judgements made about a topic, including importance assessments and trend predictions."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = RetrieveHistoricalJudgementsInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            judgements = await retrieval_service.retrieve_topic_judgements(
                params.topic_id,
                judgement_type=params.judgement_type,
                limit=params.limit,
            )

            # Convert to serializable format
            judgement_data = [
                {
                    "id": j.id,
                    "agent_name": j.agent_name,
                    "judgement_type": j.judgement_type,
                    "judgement": j.judgement,
                    "confidence": j.confidence,
                    "created_at": j.created_at.isoformat(),
                    "later_outcome": j.later_outcome,
                }
                for j in judgements
            ]

            return ToolResult.ok({
                    "topic_id": params.topic_id,
                    "judgement_count": len(judgement_data),
                    "judgements": judgement_data,
                },
            )

        except Exception as e:
            logger.error(f"Error retrieving judgements: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


# ============ Tool Registry ============


def get_historian_tools() -> list[BaseTool]:
    """Get all Historian tools.

    Returns:
        List of Historian tool instances.
    """
    return [
        RetrieveTopicTimelineTool(),
        RetrieveTopicSnapshotsTool(),
        RetrieveRelatedTopicsTool(),
        RetrieveEntityMemoriesTool(),
        RetrieveHistoricalJudgementsTool(),
    ]


def register_historian_tools(registry: "ToolRegistry") -> None:
    """Register Historian tools with a registry.

    Args:
        registry: Tool registry to register with.
    """
    for tool in get_historian_tools():
        registry.register(tool)
