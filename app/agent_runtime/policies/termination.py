"""Termination policy for agent execution.

This module defines when an agent should stop executing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.agent_runtime.state import AgentState
    from app.agent_runtime.planner import PlannerDecision

logger = get_logger(__name__)


class TerminationReason(StrEnum):
    """Reasons for terminating agent execution."""

    MAX_STEPS_REACHED = "max_steps_reached"
    FINAL_OUTPUT = "final_output"
    ERROR = "error"
    REPEATED_TOOL_LOOP = "repeated_tool_loop"
    INVALID_OUTPUT_THRESHOLD = "invalid_output_threshold"
    USER_CANCELLED = "user_cancelled"
    TIMEOUT = "timeout"


@dataclass
class TerminationResult:
    """Result of termination check."""

    should_terminate: bool
    reason: TerminationReason | None = None
    message: str = ""


class TerminationPolicy(ABC):
    """Abstract base class for termination policies."""

    @abstractmethod
    def should_terminate(
        self,
        state: "AgentState",
        decision: "PlannerDecision | None" = None,
    ) -> TerminationResult:
        """Check if execution should terminate.

        Args:
            state: Current agent state.
            decision: Latest planner decision.

        Returns:
            TerminationResult indicating whether to stop.
        """
        pass


@dataclass
class TerminationConfig:
    """Configuration for termination policy."""

    # Maximum number of steps
    max_steps: int = 10

    # Maximum consecutive errors
    max_consecutive_errors: int = 3

    # Maximum repeated tool calls (same tool, same args)
    max_repeated_tool_calls: int = 3

    # Maximum invalid outputs before termination
    max_invalid_outputs: int = 5


class DefaultTerminationPolicy(TerminationPolicy):
    """Default termination policy implementation.

    Terminates when:
    - Max steps reached
    - Final output present
    - Too many consecutive errors
    - Repeated tool loop detected
    - Too many invalid outputs
    """

    def __init__(self, config: TerminationConfig | None = None) -> None:
        """Initialize the policy.

        Args:
            config: Termination configuration.
        """
        self._config = config or TerminationConfig()
        self._consecutive_errors = 0
        self._invalid_outputs = 0
        self._recent_tool_calls: list[tuple[str, str]] = []  # (tool_name, args_hash)

    def should_terminate(
        self,
        state: "AgentState",
        decision: "PlannerDecision | None" = None,
    ) -> TerminationResult:
        """Check if execution should terminate."""
        from app.agent_runtime.planner import PlannerActionType

        # Check max steps
        if state.step_count >= self._config.max_steps:
            logger.warning(f"Max steps ({self._config.max_steps}) reached")
            return TerminationResult(
                should_terminate=True,
                reason=TerminationReason.MAX_STEPS_REACHED,
                message=f"Maximum steps ({self._config.max_steps}) reached",
            )

        # Check for final output
        if decision and decision.action_type == PlannerActionType.FINAL:
            logger.info("Final output received")
            return TerminationResult(
                should_terminate=True,
                reason=TerminationReason.FINAL_OUTPUT,
                message="Agent produced final output",
            )

        # Check for error
        if decision and decision.action_type == PlannerActionType.ERROR:
            self._consecutive_errors += 1
            if self._consecutive_errors >= self._config.max_consecutive_errors:
                logger.error(f"Max consecutive errors ({self._config.max_consecutive_errors}) reached")
                return TerminationResult(
                    should_terminate=True,
                    reason=TerminationReason.ERROR,
                    message=f"Too many consecutive errors ({self._consecutive_errors})",
                )
        else:
            self._consecutive_errors = 0

        # Check for repeated tool loop
        if decision and decision.is_tool_call and decision.tool_calls:
            tool_call = decision.tool_calls[0]
            args_hash = str(sorted(tool_call.arguments.items()))
            call_signature = (tool_call.tool_name, args_hash)

            # Count recent occurrences
            recent_count = sum(1 for tc in self._recent_tool_calls if tc == call_signature)
            if recent_count >= self._config.max_repeated_tool_calls:
                logger.warning(f"Repeated tool loop detected: {tool_call.tool_name}")
                return TerminationResult(
                    should_terminate=True,
                    reason=TerminationReason.REPEATED_TOOL_LOOP,
                    message=f"Tool {tool_call.tool_name} called repeatedly with same arguments",
                )

            # Track this call
            self._recent_tool_calls.append(call_signature)
            # Keep only recent calls
            if len(self._recent_tool_calls) > 10:
                self._recent_tool_calls = self._recent_tool_calls[-10:]

        # Check invalid outputs
        if decision and decision.action_type == PlannerActionType.THINK:
            # THINK without progress might indicate invalid output
            self._invalid_outputs += 1
            if self._invalid_outputs >= self._config.max_invalid_outputs:
                logger.warning(f"Max invalid outputs ({self._config.max_invalid_outputs}) reached")
                return TerminationResult(
                    should_terminate=True,
                    reason=TerminationReason.INVALID_OUTPUT_THRESHOLD,
                    message="Too many outputs without progress",
                )
        else:
            self._invalid_outputs = 0

        return TerminationResult(should_terminate=False)

    def reset(self) -> None:
        """Reset policy state for new execution."""
        self._consecutive_errors = 0
        self._invalid_outputs = 0
        self._recent_tool_calls = []
