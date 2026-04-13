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


class PlannerDecisionDTO(BaseModel):
    """DTO for planner decision output."""

    action_type: str  # final, tool_call, think, error
    content: str = ""
    tool_calls: list[ToolCallDTO] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentStepResultDTO(BaseModel):
    """DTO for a single agent step result."""

    step_index: int
    action_type: str
    decision: PlannerDecisionDTO | None = None
    tool_results: list[ToolResultDTO] = Field(default_factory=list)
    observation: str | None = None
    status: str = "completed"  # completed, failed, skipped
    error: str | None = None
    duration_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolCallRequestDTO(BaseModel):
    """DTO for tool call request."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str | None = None


class ToolExecutionResultDTO(BaseModel):
    """DTO for tool execution result."""

    call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class AgentRunResultDTO(BaseModel):
    """DTO for complete agent run result."""

    run_id: str
    agent_name: str
    status: str  # completed, failed, max_steps, timeout
    final_output: str | None = None
    steps: list[AgentStepResultDTO] = Field(default_factory=list)
    total_steps: int = 0
    total_duration_ms: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
