"""Observation module for agent runtime.

This module handles converting tool results to observation messages
and writing them back to agent state.
"""

from datetime import datetime, timezone
from typing import Any

from app.bootstrap.logging import get_logger
from app.agent_runtime.messages import ObservationMessage, ToolMessage
from app.agent_runtime.tools.executor import ExecutionResult

logger = get_logger(__name__)


class ObservationBuilder:
    """Builds observation messages from tool results.

    Converts tool execution results into formatted observation
    messages that can be added to agent state.
    """

    def __init__(
        self,
        *,
        max_output_length: int = 4000,
        truncation_suffix: str = "\n... [output truncated]",
        include_metadata: bool = False,
    ) -> None:
        """Initialize the builder.

        Args:
            max_output_length: Maximum length of output in observation.
            truncation_suffix: Suffix to add when truncating.
            include_metadata: Whether to include execution metadata.
        """
        self._max_output_length = max_output_length
        self._truncation_suffix = truncation_suffix
        self._include_metadata = include_metadata

    def build_observation(
        self,
        result: ExecutionResult,
    ) -> ObservationMessage:
        """Build observation message from execution result.

        Args:
            result: Tool execution result.

        Returns:
            ObservationMessage for agent state.
        """
        content = self._format_result(result)

        metadata: dict[str, Any] = {
            "call_id": result.call_id,
            "tool_name": result.tool_name,
            "success": result.success,
            "duration_ms": result.duration_ms,
        }

        if self._include_metadata and result.result.metadata:
            metadata["tool_metadata"] = result.result.metadata

        return ObservationMessage(
            content=content,
            metadata=metadata,
        )

    def build_tool_message(
        self,
        result: ExecutionResult,
    ) -> ToolMessage:
        """Build tool message from execution result.

        Args:
            result: Tool execution result.

        Returns:
            ToolMessage for agent state.
        """
        content = self._format_result(result)

        return ToolMessage(
            content=content,
            tool_name=result.tool_name,
            metadata={
                "call_id": result.call_id,
                "success": result.success,
                "duration_ms": result.duration_ms,
            },
        )

    def _format_result(self, result: ExecutionResult) -> str:
        """Format execution result as string.

        Args:
            result: Execution result.

        Returns:
            Formatted string.
        """
        if result.success:
            output = result.output
            if output is None:
                return f"Tool '{result.tool_name}' completed successfully."

            # Format output
            if isinstance(output, str):
                formatted = output
            elif isinstance(output, dict):
                import json
                formatted = json.dumps(output, ensure_ascii=False, indent=2)
            elif isinstance(output, list):
                import json
                formatted = json.dumps(output, ensure_ascii=False, indent=2)
            else:
                formatted = str(output)

            # Truncate if needed
            if len(formatted) > self._max_output_length:
                formatted = formatted[: self._max_output_length - len(self._truncation_suffix)]
                formatted += self._truncation_suffix

            return formatted
        else:
            return f"Error executing '{result.tool_name}': {result.error}"

    def build_multi_observation(
        self,
        results: list[ExecutionResult],
    ) -> ObservationMessage:
        """Build single observation from multiple results.

        Args:
            results: List of execution results.

        Returns:
            Combined ObservationMessage.
        """
        parts: list[str] = []

        for result in results:
            header = f"[{result.tool_name}]"
            content = self._format_result(result)
            parts.append(f"{header}\n{content}")

        combined = "\n\n".join(parts)

        # Truncate combined if needed
        if len(combined) > self._max_output_length:
            combined = combined[: self._max_output_length - len(self._truncation_suffix)]
            combined += self._truncation_suffix

        return ObservationMessage(
            content=combined,
            metadata={
                "tool_count": len(results),
                "tools": [r.tool_name for r in results],
            },
        )


def format_observation(result: ExecutionResult) -> str:
    """Format execution result as observation string.

    Convenience function for simple formatting.

    Args:
        result: Execution result.

    Returns:
        Formatted observation string.
    """
    builder = ObservationBuilder()
    return builder._format_result(result)


def create_observation_message(
    result: ExecutionResult,
    **kwargs: Any,
) -> ObservationMessage:
    """Create observation message from result.

    Convenience function.

    Args:
        result: Execution result.
        **kwargs: Additional builder options.

    Returns:
        ObservationMessage.
    """
    builder = ObservationBuilder(**kwargs)
    return builder.build_observation(result)
