"""Agent runtime state management."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.agent_runtime.messages import BaseMessage


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCall(BaseModel):
    """Represents a tool call request."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Represents a tool call result."""

    call_id: str
    name: str
    output: Any
    error: str | None = None


class AgentState(BaseModel):
    """Agent execution state."""

    step_count: int = 0
    max_steps: int = 10
    messages: list[BaseMessage] = Field(default_factory=list)
    tool_history: list[ToolResult] = Field(default_factory=list)
    intermediate_results: dict[str, Any] = Field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE

    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)

    def add_tool_result(self, result: ToolResult) -> None:
        self.tool_history.append(result)

    def increment_step(self) -> bool:
        """Increment step count. Returns False if max reached."""
        self.step_count += 1
        return self.step_count < self.max_steps
