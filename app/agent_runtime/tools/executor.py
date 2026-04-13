"""Tool executor for agent runtime.

This module provides execution of tools with error handling and result wrapping.
"""

import time
from dataclasses import dataclass, field
from typing import Any

from app.bootstrap.logging import get_logger
from app.agent_runtime.tools.base import BaseTool, ToolResult
from app.agent_runtime.tools.registry import ToolRegistry, get_global_registry

logger = get_logger(__name__)


@dataclass
class ExecutionContext:
    """Context for tool execution."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of tool execution with metadata."""

    call_id: str
    tool_name: str
    result: ToolResult
    duration_ms: float = 0.0
    executed_at: float = 0.0

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.result.success

    @property
    def output(self) -> Any:
        """Get execution output."""
        return self.result.output

    @property
    def error(self) -> str | None:
        """Get error message if failed."""
        return self.result.error

    def to_observation(self) -> str:
        """Convert to observation string for agent.

        Returns:
            Formatted observation string.
        """
        if self.success:
            output = self.result.output
            if isinstance(output, str):
                return output
            elif isinstance(output, dict):
                import json
                return json.dumps(output, ensure_ascii=False, indent=2)
            else:
                return str(output)
        else:
            return f"Error: {self.error}"


class ToolExecutor:
    """Executor for running tools.

    Handles tool lookup, execution, error handling, and result wrapping.
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        default_timeout: float | None = None,
    ) -> None:
        """Initialize the executor.

        Args:
            registry: Tool registry to use.
            default_timeout: Default timeout for tool execution.
        """
        self._registry = registry or get_global_registry()
        self._default_timeout = default_timeout

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        *,
        call_id: str | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            call_id: Optional call ID for tracking.
            timeout: Optional timeout override.

        Returns:
            ExecutionResult with output or error.
        """
        import uuid

        call_id = call_id or str(uuid.uuid4())[:8]
        arguments = arguments or {}
        start_time = time.perf_counter()
        executed_at = time.time()

        logger.debug(f"Executing tool '{tool_name}' (call_id={call_id})")

        # Get tool from registry
        tool = self._registry.get(tool_name)
        if tool is None:
            logger.error(f"Tool '{tool_name}' not found")
            return ExecutionResult(
                call_id=call_id,
                tool_name=tool_name,
                result=ToolResult.fail(f"Tool '{tool_name}' not found"),
                duration_ms=0.0,
                executed_at=executed_at,
            )

        # Execute tool
        try:
            result = await tool.safe_execute(**arguments)
            duration_ms = (time.perf_counter() - start_time) * 1000

            if result.success:
                logger.info(
                    f"Tool '{tool_name}' executed successfully "
                    f"(call_id={call_id}, duration={duration_ms:.1f}ms)"
                )
            else:
                logger.warning(
                    f"Tool '{tool_name}' failed: {result.error} "
                    f"(call_id={call_id})"
                )

            return ExecutionResult(
                call_id=call_id,
                tool_name=tool_name,
                result=result,
                duration_ms=duration_ms,
                executed_at=executed_at,
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Tool '{tool_name}' raised exception: {e}")

            return ExecutionResult(
                call_id=call_id,
                tool_name=tool_name,
                result=ToolResult.fail(str(e)),
                duration_ms=duration_ms,
                executed_at=executed_at,
            )

    async def execute_context(self, context: ExecutionContext) -> ExecutionResult:
        """Execute a tool from context.

        Args:
            context: Execution context.

        Returns:
            ExecutionResult.
        """
        return await self.execute(
            tool_name=context.tool_name,
            arguments=context.arguments,
            call_id=context.call_id,
            timeout=context.timeout_seconds,
        )

    async def execute_many(
        self,
        calls: list[tuple[str, dict[str, Any]]],
    ) -> list[ExecutionResult]:
        """Execute multiple tools sequentially.

        Args:
            calls: List of (tool_name, arguments) tuples.

        Returns:
            List of ExecutionResults.
        """
        results: list[ExecutionResult] = []
        for tool_name, arguments in calls:
            result = await self.execute(tool_name, arguments)
            results.append(result)
        return results

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names.

        Returns:
            List of tool names.
        """
        return self._registry.list_tools()

    def has_tool(self, name: str) -> bool:
        """Check if a tool is available.

        Args:
            name: Tool name.

        Returns:
            True if tool exists.
        """
        return self._registry.has(name)


# Singleton executor
_default_executor: ToolExecutor | None = None


def get_tool_executor() -> ToolExecutor:
    """Get the default tool executor.

    Returns:
        The default ToolExecutor instance.
    """
    global _default_executor
    if _default_executor is None:
        _default_executor = ToolExecutor()
    return _default_executor
