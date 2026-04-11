"""Tool protocol definitions."""

from typing import Any, Protocol

from pydantic import BaseModel


class ToolProtocol(Protocol):
    """Protocol for tool implementations."""

    @property
    def name(self) -> str:
        """Tool name."""
        ...

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        ...

    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with given arguments."""
        ...

    def get_schema(self) -> dict[str, Any]:
        """Get JSON schema for tool arguments."""
        ...
