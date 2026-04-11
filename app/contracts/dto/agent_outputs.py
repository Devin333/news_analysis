"""Agent runtime output DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCallDTO(BaseModel):
    """Tool call request payload."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultDTO(BaseModel):
    """Tool execution result payload."""

    call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error_message: str | None = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class AgentStepRecordDTO(BaseModel):
    """Single step execution record."""

    step_index: int
    thought: str | None = None
    tool_call: ToolCallDTO | None = None
    tool_result: ToolResultDTO | None = None
    observation: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentFinalOutputDTO(BaseModel):
    """Final output of an agent run."""

    status: str
    final_answer: str | None = None
    steps: list[AgentStepRecordDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
