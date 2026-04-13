"""Analysis tools for Analyst Agent.

Provides tools for retrieving metrics, items, tags,
and other context needed for value analysis.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.agent_runtime.tools.base import BaseTool, ToolResult
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


# ============ Tool Input Schemas ============


class GetTopicMetricsInput(BaseModel):
    """Input for get_topic_metrics tool."""

    topic_id: int = Field(description="The topic ID to get metrics for")


class GetRecentTopicItemsInput(BaseModel):
    """Input for get_recent_topic_items tool."""

    topic_id: int = Field(description="The topic ID to get items for")
    limit: int = Field(default=10, description="Maximum number of items to return")


class GetTopicTagsInput(BaseModel):
    """Input for get_topic_tags tool."""

    topic_id: int = Field(description="The topic ID to get tags for")


class GetHistorianOutputInput(BaseModel):
    """Input for get_historian_output tool."""

    topic_id: int = Field(description="The topic ID to get historian output for")


class GetRelatedEntityActivityInput(BaseModel):
    """Input for get_related_entity_activity tool."""

    topic_id: int = Field(description="The topic ID to get entity activity for")
    limit: int = Field(default=5, description="Maximum number of entities")


class GetRecentJudgementsInput(BaseModel):
    """Input for get_recent_judgements_for_topic tool."""

    topic_id: int = Field(description="The topic ID to get judgements for")
    limit: int = Field(default=10, description="Maximum number of judgements")


# ============ Tool Implementations ============


class GetTopicMetricsTool(BaseTool):
    """Tool to get topic metrics."""

    name: str = "get_topic_metrics"
    description: str = "Get detailed metrics for a topic including item count, source count, heat score, and trend score."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = GetTopicMetricsInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            # Get topic info
            topic = await retrieval_service.get_topic_info(params.topic_id)
            if topic is None:
                return ToolResult(
                    success=False,
                    error=f"Topic {params.topic_id} not found",
                )

            return ToolResult(
                success=True,
                data={
                    "topic_id": params.topic_id,
                    "item_count": topic.item_count,
                    "source_count": topic.source_count,
                    "heat_score": topic.heat_score,
                    "trend_score": topic.trend_score,
                    "first_seen_at": topic.first_seen_at.isoformat() if topic.first_seen_at else None,
                    "last_seen_at": topic.last_seen_at.isoformat() if topic.last_seen_at else None,
                },
            )

        except Exception as e:
            logger.error(f"Error getting topic metrics: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class GetRecentTopicItemsTool(BaseTool):
    """Tool to get recent items for a topic."""

    name: str = "get_recent_topic_items"
    description: str = "Get recent items in a topic for analysis."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = GetRecentTopicItemsInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            items = await retrieval_service.retrieve_recent_topic_items(
                params.topic_id,
                limit=params.limit,
            )

            item_data = [
                {
                    "id": item.id,
                    "title": item.title,
                    "excerpt": item.excerpt[:200] if item.excerpt else None,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "content_type": item.content_type,
                }
                for item in items
            ]

            return ToolResult(
                success=True,
                data={
                    "topic_id": params.topic_id,
                    "item_count": len(item_data),
                    "items": item_data,
                },
            )

        except Exception as e:
            logger.error(f"Error getting recent items: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class GetTopicTagsTool(BaseTool):
    """Tool to get topic tags."""

    name: str = "get_topic_tags"
    description: str = "Get tags associated with a topic."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = GetTopicTagsInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            tags = await retrieval_service.retrieve_topic_tags(params.topic_id)

            return ToolResult(
                success=True,
                data={
                    "topic_id": params.topic_id,
                    "tag_count": len(tags),
                    "tags": tags,
                },
            )

        except Exception as e:
            logger.error(f"Error getting topic tags: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class GetHistorianOutputTool(BaseTool):
    """Tool to get historian output for a topic."""

    name: str = "get_historian_output"
    description: str = "Get historical analysis from Historian agent for a topic."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = GetHistorianOutputInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            historian_output = await retrieval_service.retrieve_historian_output(
                params.topic_id
            )

            if historian_output is None:
                return ToolResult(
                    success=True,
                    data={
                        "topic_id": params.topic_id,
                        "has_historian_output": False,
                    },
                )

            return ToolResult(
                success=True,
                data={
                    "topic_id": params.topic_id,
                    "has_historian_output": True,
                    "historical_status": historian_output.get("historical_status"),
                    "current_stage": historian_output.get("current_stage"),
                    "history_summary": historian_output.get("history_summary"),
                    "what_is_new_this_time": historian_output.get("what_is_new_this_time"),
                    "historical_confidence": historian_output.get("historical_confidence"),
                },
            )

        except Exception as e:
            logger.error(f"Error getting historian output: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class GetRelatedEntityActivityTool(BaseTool):
    """Tool to get related entity activity."""

    name: str = "get_related_entity_activity"
    description: str = "Get activity of entities related to a topic."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = GetRelatedEntityActivityInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            entities = await retrieval_service.retrieve_topic_entities(
                params.topic_id,
                limit=params.limit,
            )

            entity_data = [
                {
                    "entity_id": e.entity_id,
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "activity_score": e.activity_score,
                }
                for e in entities
            ]

            return ToolResult(
                success=True,
                data={
                    "topic_id": params.topic_id,
                    "entity_count": len(entity_data),
                    "entities": entity_data,
                },
            )

        except Exception as e:
            logger.error(f"Error getting entity activity: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


class GetRecentJudgementsTool(BaseTool):
    """Tool to get recent judgements for a topic."""

    name: str = "get_recent_judgements_for_topic"
    description: str = "Get recent system judgements made about a topic."

    async def execute(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool."""
        try:
            params = GetRecentJudgementsInput(**input_data)

            retrieval_service = self._get_retrieval_service()
            if retrieval_service is None:
                return ToolResult(
                    success=False,
                    error="Retrieval service not available",
                )

            judgements = await retrieval_service.retrieve_topic_judgements(
                params.topic_id,
                limit=params.limit,
            )

            judgement_data = [
                {
                    "id": j.id,
                    "agent_name": j.agent_name,
                    "judgement_type": j.judgement_type,
                    "judgement": j.judgement,
                    "confidence": j.confidence,
                    "created_at": j.created_at.isoformat(),
                }
                for j in judgements
            ]

            return ToolResult(
                success=True,
                data={
                    "topic_id": params.topic_id,
                    "judgement_count": len(judgement_data),
                    "judgements": judgement_data,
                },
            )

        except Exception as e:
            logger.error(f"Error getting judgements: {e}")
            return ToolResult(success=False, error=str(e))

    def _get_retrieval_service(self):
        return getattr(self, "_retrieval_service", None)


# ============ Tool Registry ============


def get_analyst_tools() -> list[BaseTool]:
    """Get all Analyst tools.

    Returns:
        List of Analyst tool instances.
    """
    return [
        GetTopicMetricsTool(),
        GetRecentTopicItemsTool(),
        GetTopicTagsTool(),
        GetHistorianOutputTool(),
        GetRelatedEntityActivityTool(),
        GetRecentJudgementsTool(),
    ]


def register_analyst_tools(registry: "ToolRegistry") -> None:
    """Register Analyst tools with a registry.

    Args:
        registry: Tool registry to register with.
    """
    for tool in get_analyst_tools():
        registry.register(tool)
