"""Agent step executor for runtime.

This module provides the executor that runs a single agent step:
1. Read current state
2. Call planner/LLM
3. Parse output
4. Execute tools if needed
5. Write back observation
"""

import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.agent_runtime.planner import (
    PlannerActionType,
    PlannerDecision,
    PlannerOutput,
    parse_planner_response,
    create_error_decision,
)
from app.agent_runtime.state import AgentState, AgentStatus, StepRecord, ToolCall
from app.agent_runtime.observation import ObservationBuilder
from app.agent_runtime.tools.executor import ToolExecutor, get_tool_executor

if TYPE_CHECKING:
    from app.contracts.protocols.llm import LLMClientProtocol

logger = get_logger(__name__)


@dataclass
class StepResult:
    """Result of executing a single step."""

    decision: PlannerDecision
    step_record: StepRecord
    should_continue: bool = True
    final_output: str | None = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class ExecutorConfig:
    """Configuration for step executor."""

    # Maximum tool calls per step
    max_tool_calls_per_step: int = 5

    # Whether to include tool results in observation
    include_tool_metadata: bool = False

    # Maximum observation length
    max_observation_length: int = 4000


class StepExecutor:
    """Executes a single agent step.

    Responsibilities:
    - Call LLM with current state
    - Parse LLM response into decision
    - Execute tools if needed
    - Write observation back to state
    """

    def __init__(
        self,
        llm_client: "LLMClientProtocol | None" = None,
        tool_executor: ToolExecutor | None = None,
        config: ExecutorConfig | None = None,
    ) -> None:
        """Initialize the executor.

        Args:
            llm_client: LLM client for calling the model.
            tool_executor: Tool executor for running tools.
            config: Executor configuration.
        """
        self._llm_client = llm_client
        self._tool_executor = tool_executor or get_tool_executor()
        self._config = config or ExecutorConfig()
        self._observation_builder = ObservationBuilder(
            max_output_length=self._config.max_observation_length,
            include_metadata=self._config.include_tool_metadata,
        )

    async def execute_step(
        self,
        state: AgentState,
        *,
        system_prompt: str | None = None,
        available_tools: list[str] | None = None,
    ) -> StepResult:
        """Execute a single agent step.

        Args:
            state: Current agent state.
            system_prompt: Optional system prompt override.
            available_tools: List of available tool names.

        Returns:
            StepResult with decision and updated state.
        """
        start_time = time.perf_counter()
        step_index = state.step_count

        logger.debug(f"Executing step {step_index}")

        # Update state
        state.set_running()

        try:
            # Get LLM response
            planner_output = await self._call_llm(state, system_prompt)
            decision = planner_output.decision

            # Create step record
            step_record = StepRecord(
                step_index=step_index,
                action_type=decision.action_type.value,
                assistant_message=decision.content or decision.reasoning,
            )

            # Add assistant message to state
            if decision.content or decision.reasoning:
                state.add_assistant_message(decision.content or decision.reasoning)

            # Handle different action types
            if decision.is_final:
                # Final answer
                state.set_completed(decision.content)
                duration_ms = (time.perf_counter() - start_time) * 1000
                step_record.duration_ms = duration_ms

                logger.info(f"Step {step_index}: Final answer produced")

                return StepResult(
                    decision=decision,
                    step_record=step_record,
                    should_continue=False,
                    final_output=decision.content,
                    duration_ms=duration_ms,
                )

            elif decision.is_tool_call:
                # Execute tools
                await self._execute_tools(state, decision, step_record)

                duration_ms = (time.perf_counter() - start_time) * 1000
                step_record.duration_ms = duration_ms

                logger.info(
                    f"Step {step_index}: Executed {len(decision.tool_calls)} tool(s)"
                )

                return StepResult(
                    decision=decision,
                    step_record=step_record,
                    should_continue=True,
                    duration_ms=duration_ms,
                )

            elif decision.is_error:
                # Error occurred
                state.set_failed(decision.content)
                duration_ms = (time.perf_counter() - start_time) * 1000
                step_record.duration_ms = duration_ms

                logger.error(f"Step {step_index}: Error - {decision.content}")

                return StepResult(
                    decision=decision,
                    step_record=step_record,
                    should_continue=False,
                    error=decision.content,
                    duration_ms=duration_ms,
                )

            else:
                # Think/reasoning step
                duration_ms = (time.perf_counter() - start_time) * 1000
                step_record.duration_ms = duration_ms

                logger.debug(f"Step {step_index}: Thinking/reasoning")

                return StepResult(
                    decision=decision,
                    step_record=step_record,
                    should_continue=True,
                    duration_ms=duration_ms,
                )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = str(e)

            logger.error(f"Step {step_index} failed: {error_msg}")

            decision = create_error_decision(error_msg)
            step_record = StepRecord(
                step_index=step_index,
                action_type="error",
                duration_ms=duration_ms,
            )

            return StepResult(
                decision=decision,
                step_record=step_record,
                should_continue=False,
                error=error_msg,
                duration_ms=duration_ms,
            )

    async def _call_llm(
        self,
        state: AgentState,
        system_prompt: str | None = None,
    ) -> PlannerOutput:
        """Call LLM and get planner output.

        Args:
            state: Current agent state.
            system_prompt: Optional system prompt.

        Returns:
            PlannerOutput with decision.
        """
        if self._llm_client is None:
            # Return a mock response for testing
            logger.warning("No LLM client configured, using mock response")
            return PlannerOutput(
                decision=create_error_decision("No LLM client configured"),
                raw_response="",
            )

        # Build messages for LLM
        messages = state.get_conversation_for_llm()

        # Add system prompt if provided
        if system_prompt and (not messages or messages[0].get("role") != "system"):
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Call LLM
        start_time = time.perf_counter()
        response = await self._llm_client.complete(messages)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Parse response
        available_tools = self._tool_executor.get_available_tools()
        decision = parse_planner_response(response.content, available_tools=available_tools)

        return PlannerOutput(
            decision=decision,
            raw_response=response.content,
            model_name=response.model or "",
            token_usage=response.usage or {},
            latency_ms=latency_ms,
        )

    async def _execute_tools(
        self,
        state: AgentState,
        decision: PlannerDecision,
        step_record: StepRecord,
    ) -> None:
        """Execute tools from decision.

        Args:
            state: Agent state to update.
            decision: Decision with tool calls.
            step_record: Step record to update.
        """
        tool_calls = decision.tool_calls[: self._config.max_tool_calls_per_step]

        for tool_call in tool_calls:
            # Record tool call
            step_record.tool_calls.append(
                ToolCall(
                    id=tool_call.call_id or "",
                    name=tool_call.tool_name,
                    arguments=tool_call.arguments,
                )
            )

            # Execute tool
            result = await self._tool_executor.execute(
                tool_name=tool_call.tool_name,
                arguments=tool_call.arguments,
                call_id=tool_call.call_id,
            )

            # Add result to state
            state.add_tool_result_from_execution(result)

            # Record result
            from app.agent_runtime.state import ToolResult as StateToolResult
            step_record.tool_results.append(
                StateToolResult(
                    call_id=result.call_id,
                    name=result.tool_name,
                    output=result.output,
                    error=result.error,
                    success=result.success,
                )
            )

            # Build observation
            observation = self._observation_builder.build_observation(result)
            step_record.observation = observation.content
