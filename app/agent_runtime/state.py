"""Agent runtime state management."""

from enum import StrEnum
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, Field

from app.agent_runtime.messages import (
    BaseMessage,
    AssistantMessage,
    ObservationMessage,
    SystemMessage,
    ToolMessage,
    UserMessage,
)

if TYPE_CHECKING:
    from app.agent_runtime.tools.executor import ExecutionResult


class AgentStatus(StrEnum):
    """Status of agent execution."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
    success: bool = True


class StepRecord(BaseModel):
    """Record of a single execution step."""

    step_index: int
    action_type: str  # final, tool_call, think, error
    assistant_message: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    observation: str | None = None
    duration_ms: float = 0.0


class AgentState(BaseModel):
    """Agent execution state.

    Manages messages, tool history, and execution status.
    """

    # Execution tracking
    step_count: int = 0
    max_steps: int = 10

    # Message history
    messages: list[BaseMessage] = Field(default_factory=list)

    # Tool execution history
    tool_history: list[ToolResult] = Field(default_factory=list)

    # Step records for tracing
    step_records: list[StepRecord] = Field(default_factory=list)

    # Intermediate results storage
    intermediate_results: dict[str, Any] = Field(default_factory=dict)

    # Current status
    status: AgentStatus = AgentStatus.IDLE

    # Final output
    final_output: str | None = None

    # Error tracking
    last_error: str | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to history."""
        self.messages.append(message)

    def add_system_message(self, content: str) -> None:
        """Add a system message."""
        self.messages.append(SystemMessage(content=content))

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.messages.append(UserMessage(content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message."""
        self.messages.append(AssistantMessage(content=content))

    def add_tool_message(self, content: str, tool_name: str) -> None:
        """Add a tool message."""
        self.messages.append(ToolMessage(content=content, tool_name=tool_name))

    def add_observation(self, content: str) -> None:
        """Add an observation message."""
        self.messages.append(ObservationMessage(content=content))

    def add_tool_result(self, result: ToolResult) -> None:
        """Add a tool result to history."""
        self.tool_history.append(result)

    def add_tool_result_from_execution(
        self,
        execution_result: "ExecutionResult",
    ) -> None:
        """Add tool result from ExecutionResult."""
        result = ToolResult(
            call_id=execution_result.call_id,
            name=execution_result.tool_name,
            output=execution_result.output,
            error=execution_result.error,
            success=execution_result.success,
        )
        self.tool_history.append(result)

        # Also add observation message
        self.add_observation(execution_result.to_observation())

    def add_step_record(self, record: StepRecord) -> None:
        """Add a step record."""
        self.step_records.append(record)

    def increment_step(self) -> bool:
        """Increment step count.

        Returns:
            False if max steps reached.
        """
        self.step_count += 1
        return self.step_count < self.max_steps

    def can_continue(self) -> bool:
        """Check if execution can continue."""
        return (
            self.step_count < self.max_steps
            and self.status in (AgentStatus.IDLE, AgentStatus.RUNNING, AgentStatus.WAITING_TOOL)
        )

    def set_running(self) -> None:
        """Set status to running."""
        self.status = AgentStatus.RUNNING

    def set_completed(self, output: str | None = None) -> None:
        """Set status to completed."""
        self.status = AgentStatus.COMPLETED
        self.final_output = output

    def set_failed(self, error: str) -> None:
        """Set status to failed."""
        self.status = AgentStatus.FAILED
        self.last_error = error

    def set_cancelled(self) -> None:
        """Set status to cancelled."""
        self.status = AgentStatus.CANCELLED

    def get_last_assistant_message(self) -> str | None:
        """Get the last assistant message content."""
        for msg in reversed(self.messages):
            if isinstance(msg, AssistantMessage):
                return msg.content
        return None

    def get_conversation_for_llm(self) -> list[dict[str, str]]:
        """Get messages formatted for LLM API.

        Returns:
            List of message dicts with role and content.
        """
        result: list[dict[str, str]] = []
        for msg in self.messages:
            role = msg.role
            # Map observation to assistant or tool role
            if role == "observation":
                role = "assistant"
            result.append({"role": role, "content": msg.content})
        return result

    def reset(self) -> None:
        """Reset state for new execution."""
        self.step_count = 0
        self.messages = []
        self.tool_history = []
        self.step_records = []
        self.intermediate_results = {}
        self.status = AgentStatus.IDLE
        self.final_output = None
        self.last_error = None
