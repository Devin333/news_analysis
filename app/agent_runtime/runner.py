"""Agent runner for executing complete agent workflows.

This module provides the runner that orchestrates multi-step agent execution.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.agent_runtime.state import AgentState, AgentStatus
from app.agent_runtime.executor import StepExecutor, StepResult
from app.agent_runtime.policies.termination import (
    DefaultTerminationPolicy,
    TerminationPolicy,
    TerminationReason,
)
from app.agent_runtime.policies.retry import (
    DefaultRetryPolicy,
    RetryPolicy,
    RetryAction,
)
from app.agent_runtime.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from app.contracts.protocols.llm import LLMClientProtocol

logger = get_logger(__name__)


@dataclass
class RunConfig:
    """Configuration for agent run."""

    max_steps: int = 10
    system_prompt: str | None = None
    timeout_seconds: float | None = None
    enable_tracing: bool = True


@dataclass
class RunResult:
    """Result of a complete agent run."""

    run_id: str
    status: str  # completed, failed, max_steps, timeout, cancelled
    final_output: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    total_steps: int = 0
    total_duration_ms: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if run was successful."""
        return self.status == "completed"


class AgentRunner:
    """Runner for executing complete agent workflows.

    Orchestrates:
    - State initialization
    - Multi-step execution loop
    - Termination policy checking
    - Error handling and retry
    - Result collection
    """

    def __init__(
        self,
        llm_client: "LLMClientProtocol | None" = None,
        tool_registry: ToolRegistry | None = None,
        termination_policy: TerminationPolicy | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        """Initialize the runner.

        Args:
            llm_client: LLM client for completions.
            tool_registry: Registry of available tools.
            termination_policy: Policy for when to stop.
            retry_policy: Policy for handling failures.
        """
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._termination_policy = termination_policy or DefaultTerminationPolicy()
        self._retry_policy = retry_policy or DefaultRetryPolicy()
        self._executor: StepExecutor | None = None

    def _get_executor(self) -> StepExecutor:
        """Get or create step executor."""
        if self._executor is None:
            from app.agent_runtime.tools.executor import ToolExecutor

            tool_executor = None
            if self._tool_registry:
                tool_executor = ToolExecutor(self._tool_registry)

            self._executor = StepExecutor(
                llm_client=self._llm_client,
                tool_executor=tool_executor,
            )
        return self._executor

    async def run(
        self,
        initial_message: str,
        *,
        config: RunConfig | None = None,
        state: AgentState | None = None,
    ) -> RunResult:
        """Run the agent to completion.

        Args:
            initial_message: Initial user message.
            config: Run configuration.
            state: Optional existing state to continue.

        Returns:
            RunResult with final output and execution details.
        """
        config = config or RunConfig()
        run_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        logger.info(f"Starting agent run {run_id}")

        # Initialize state
        if state is None:
            state = AgentState(max_steps=config.max_steps)
            if config.system_prompt:
                state.add_system_message(config.system_prompt)
            state.add_user_message(initial_message)

        executor = self._get_executor()
        steps: list[StepResult] = []
        total_tokens: dict[str, int] = {}

        # Reset termination policy
        if hasattr(self._termination_policy, "reset"):
            self._termination_policy.reset()

        try:
            # Main execution loop
            while state.can_continue():
                # Execute step
                step_result = await executor.execute_step(
                    state,
                    system_prompt=config.system_prompt,
                    available_tools=self._tool_registry.list_tools() if self._tool_registry else None,
                )

                steps.append(step_result)
                state.add_step_record(step_result.step_record)
                state.increment_step()

                # Check termination
                term_result = self._termination_policy.should_terminate(
                    state,
                    step_result.decision,
                )

                if term_result.should_terminate:
                    logger.info(f"Run {run_id} terminating: {term_result.reason}")

                    if term_result.reason == TerminationReason.FINAL_OUTPUT:
                        return self._build_result(
                            run_id=run_id,
                            status="completed",
                            final_output=step_result.final_output,
                            steps=steps,
                            state=state,
                            start_time=start_time,
                        )
                    elif term_result.reason == TerminationReason.MAX_STEPS_REACHED:
                        return self._build_result(
                            run_id=run_id,
                            status="max_steps",
                            steps=steps,
                            state=state,
                            start_time=start_time,
                            error="Maximum steps reached",
                        )
                    elif term_result.reason == TerminationReason.ERROR:
                        return self._build_result(
                            run_id=run_id,
                            status="failed",
                            steps=steps,
                            state=state,
                            start_time=start_time,
                            error=step_result.error,
                        )
                    else:
                        return self._build_result(
                            run_id=run_id,
                            status="terminated",
                            steps=steps,
                            state=state,
                            start_time=start_time,
                            error=term_result.message,
                        )

                # Check if step wants to continue
                if not step_result.should_continue:
                    if step_result.final_output:
                        return self._build_result(
                            run_id=run_id,
                            status="completed",
                            final_output=step_result.final_output,
                            steps=steps,
                            state=state,
                            start_time=start_time,
                        )
                    elif step_result.error:
                        return self._build_result(
                            run_id=run_id,
                            status="failed",
                            steps=steps,
                            state=state,
                            start_time=start_time,
                            error=step_result.error,
                        )

            # Max steps reached
            return self._build_result(
                run_id=run_id,
                status="max_steps",
                steps=steps,
                state=state,
                start_time=start_time,
                error="Maximum steps reached",
            )

        except Exception as e:
            logger.error(f"Run {run_id} failed with exception: {e}")
            return self._build_result(
                run_id=run_id,
                status="failed",
                steps=steps,
                state=state,
                start_time=start_time,
                error=str(e),
            )

    def _build_result(
        self,
        *,
        run_id: str,
        status: str,
        steps: list[StepResult],
        state: AgentState,
        start_time: float,
        final_output: str | None = None,
        error: str | None = None,
    ) -> RunResult:
        """Build run result."""
        duration_ms = (time.perf_counter() - start_time) * 1000

        return RunResult(
            run_id=run_id,
            status=status,
            final_output=final_output or state.final_output,
            steps=steps,
            total_steps=len(steps),
            total_duration_ms=duration_ms,
            error=error,
            metadata={
                "state_step_count": state.step_count,
                "state_status": state.status.value,
            },
        )

    async def run_with_retry(
        self,
        initial_message: str,
        *,
        config: RunConfig | None = None,
        max_retries: int = 3,
    ) -> RunResult:
        """Run with automatic retry on failure.

        Args:
            initial_message: Initial user message.
            config: Run configuration.
            max_retries: Maximum retry attempts.

        Returns:
            RunResult from successful run or last attempt.
        """
        last_result: RunResult | None = None

        for attempt in range(max_retries):
            result = await self.run(initial_message, config=config)

            if result.success:
                return result

            last_result = result

            # Check retry policy
            retry_decision = self._retry_policy.should_retry(
                Exception(result.error or "Unknown error"),
                attempt + 1,
            )

            if retry_decision.action != RetryAction.RETRY:
                break

            # Wait before retry
            if retry_decision.delay_seconds > 0:
                import asyncio
                await asyncio.sleep(retry_decision.delay_seconds)

            logger.info(f"Retrying run (attempt {attempt + 2}/{max_retries})")

        return last_result or RunResult(
            run_id="",
            status="failed",
            error="All retry attempts failed",
        )


# Singleton runner
_default_runner: AgentRunner | None = None


def get_agent_runner() -> AgentRunner:
    """Get the default agent runner.

    Returns:
        The default AgentRunner instance.
    """
    global _default_runner
    if _default_runner is None:
        _default_runner = AgentRunner()
    return _default_runner
