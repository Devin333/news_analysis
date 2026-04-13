"""Planner module for agent decision making.

This module defines the planner output protocol and decision structures
for agent step execution.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class PlannerActionType(StrEnum):
    """Types of actions a planner can output."""

    FINAL = "final"  # Return final answer
    TOOL_CALL = "tool_call"  # Call a tool
    THINK = "think"  # Internal reasoning step
    ERROR = "error"  # Error occurred


class ToolCallRequest(BaseModel):
    """Request to call a tool."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str | None = None


class PlannerDecision(BaseModel):
    """Decision output from planner.

    Represents what action the agent should take next.
    """

    action_type: PlannerActionType
    content: str = ""  # For FINAL or THINK actions
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    reasoning: str = ""  # Internal reasoning
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_final(self) -> bool:
        """Check if this is a final decision."""
        return self.action_type == PlannerActionType.FINAL

    @property
    def is_tool_call(self) -> bool:
        """Check if this requires tool execution."""
        return self.action_type == PlannerActionType.TOOL_CALL

    @property
    def is_error(self) -> bool:
        """Check if this is an error."""
        return self.action_type == PlannerActionType.ERROR


class PlannerOutput(BaseModel):
    """Full output from planner including raw response."""

    decision: PlannerDecision
    raw_response: str = ""
    model_name: str = ""
    token_usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: float = 0.0


def parse_planner_response(
    response: str,
    *,
    available_tools: list[str] | None = None,
) -> PlannerDecision:
    """Parse raw LLM response into PlannerDecision.

    This is a simple parser that looks for structured output patterns.
    In production, you'd use structured output from the LLM.

    Args:
        response: Raw LLM response text.
        available_tools: List of available tool names.

    Returns:
        PlannerDecision parsed from response.
    """
    import json
    import re

    response_lower = response.lower().strip()

    # Check for final answer pattern
    if response_lower.startswith("final:") or "final answer:" in response_lower:
        content = response
        if "final:" in response_lower:
            content = response.split(":", 1)[1].strip()
        elif "final answer:" in response_lower:
            idx = response_lower.find("final answer:")
            content = response[idx + len("final answer:"):].strip()

        return PlannerDecision(
            action_type=PlannerActionType.FINAL,
            content=content,
        )

    # Check for tool call pattern
    # Look for JSON-like tool call
    tool_call_pattern = r'\{[^{}]*"tool"[^{}]*\}'
    matches = re.findall(tool_call_pattern, response, re.DOTALL)

    if matches:
        tool_calls: list[ToolCallRequest] = []
        for match in matches:
            try:
                data = json.loads(match)
                tool_name = data.get("tool") or data.get("name") or data.get("tool_name")
                arguments = data.get("arguments") or data.get("args") or {}

                if tool_name:
                    tool_calls.append(
                        ToolCallRequest(
                            tool_name=tool_name,
                            arguments=arguments,
                        )
                    )
            except json.JSONDecodeError:
                continue

        if tool_calls:
            return PlannerDecision(
                action_type=PlannerActionType.TOOL_CALL,
                tool_calls=tool_calls,
                reasoning=response,
            )

    # Check for explicit tool call syntax
    if available_tools:
        for tool in available_tools:
            if f"use {tool}" in response_lower or f"call {tool}" in response_lower:
                return PlannerDecision(
                    action_type=PlannerActionType.TOOL_CALL,
                    tool_calls=[ToolCallRequest(tool_name=tool)],
                    reasoning=response,
                )

    # Default to thinking/reasoning
    return PlannerDecision(
        action_type=PlannerActionType.THINK,
        content=response,
        reasoning=response,
    )


def create_final_decision(content: str, **kwargs: Any) -> PlannerDecision:
    """Create a final answer decision."""
    return PlannerDecision(
        action_type=PlannerActionType.FINAL,
        content=content,
        **kwargs,
    )


def create_tool_call_decision(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    **kwargs: Any,
) -> PlannerDecision:
    """Create a tool call decision."""
    return PlannerDecision(
        action_type=PlannerActionType.TOOL_CALL,
        tool_calls=[
            ToolCallRequest(
                tool_name=tool_name,
                arguments=arguments or {},
            )
        ],
        **kwargs,
    )


def create_error_decision(error: str, **kwargs: Any) -> PlannerDecision:
    """Create an error decision."""
    return PlannerDecision(
        action_type=PlannerActionType.ERROR,
        content=error,
        **kwargs,
    )
