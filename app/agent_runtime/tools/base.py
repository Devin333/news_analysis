"""Base tool definition for agent runtime.

This module defines the base class for all tools that agents can use.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar, Generic

from pydantic import BaseModel

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ToolArgsSchema(BaseModel):
    """Base schema for tool arguments."""

    pass


@dataclass
class ToolResult:
    """Result of tool execution."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Any, **metadata: Any) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> "ToolResult":
        """Create a failed result."""
        return cls(success=False, error=error, metadata=metadata)


@dataclass
class ToolDefinition:
    """Definition of a tool for LLM consumption."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required_params: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required_params,
                },
            },
        }


class BaseTool(ABC):
    """Abstract base class for tools.

    All tools must implement:
    - name: Unique tool identifier
    - description: Human-readable description
    - execute: The actual tool logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass

    @property
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""
        return {}

    @property
    def required_params(self) -> list[str]:
        """List of required parameter names."""
        return []

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments.

        Args:
            **kwargs: Tool arguments.

        Returns:
            ToolResult with output or error.
        """
        pass

    def validate_args(self, **kwargs: Any) -> tuple[bool, str | None]:
        """Validate tool arguments.

        Args:
            **kwargs: Arguments to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        # Check required parameters
        for param in self.required_params:
            if param not in kwargs:
                return False, f"Missing required parameter: {param}"
        return True, None

    def get_definition(self) -> ToolDefinition:
        """Get tool definition for LLM."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            required_params=self.required_params,
        )

    async def safe_execute(self, **kwargs: Any) -> ToolResult:
        """Execute with error handling.

        Args:
            **kwargs: Tool arguments.

        Returns:
            ToolResult, always returns (never raises).
        """
        try:
            # Validate arguments
            is_valid, error = self.validate_args(**kwargs)
            if not is_valid:
                return ToolResult.fail(error or "Invalid arguments")

            # Execute
            result = await self.execute(**kwargs)
            return result

        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {e}")
            return ToolResult.fail(str(e))


class SyncTool(BaseTool):
    """Base class for synchronous tools.

    Wraps sync execute in async.
    """

    @abstractmethod
    def execute_sync(self, **kwargs: Any) -> ToolResult:
        """Synchronous execution method."""
        pass

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Async wrapper for sync execution."""
        return self.execute_sync(**kwargs)
