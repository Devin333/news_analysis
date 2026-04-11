"""Agent protocol definitions."""

from typing import Any, Protocol

from app.agent_runtime.state import AgentState
from app.contracts.dto.agent_outputs import AgentFinalOutputDTO


class AgentProtocol(Protocol):
    """Protocol for agent implementations."""

    async def run(self, task: str, **context: Any) -> AgentFinalOutputDTO:
        """Execute the agent with a task description and optional context."""
        ...

    async def step(self, state: AgentState) -> AgentState:
        """Execute a single step of the agent loop."""
        ...
