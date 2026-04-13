"""Tool registry for agent runtime.

This module provides a registry for managing available tools.
"""

from typing import Any

from app.bootstrap.logging import get_logger
from app.agent_runtime.tools.base import BaseTool, ToolDefinition

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for managing tools.

    Provides methods to register, retrieve, and list tools.
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool.

        Args:
            tool: The tool to register.

        Raises:
            ValueError: If tool with same name already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def register_many(self, tools: list[BaseTool]) -> None:
        """Register multiple tools.

        Args:
            tools: List of tools to register.
        """
        for tool in tools:
            self.register(tool)

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name.

        Args:
            name: Tool name to unregister.

        Returns:
            True if tool was unregistered, False if not found.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            The tool or None if not found.
        """
        return self._tools.get(name)

    def get_required(self, name: str) -> BaseTool:
        """Get a tool by name, raising if not found.

        Args:
            name: Tool name.

        Returns:
            The tool.

        Raises:
            KeyError: If tool not found.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found")
        return tool

    def has(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: Tool name.

        Returns:
            True if tool exists.
        """
        return name in self._tools

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names.
        """
        return list(self._tools.keys())

    def list_definitions(self) -> list[ToolDefinition]:
        """List all tool definitions.

        Returns:
            List of tool definitions.
        """
        return [tool.get_definition() for tool in self._tools.values()]

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """Get tools in OpenAI function calling format.

        Returns:
            List of tool definitions in OpenAI format.
        """
        return [
            tool.get_definition().to_openai_format()
            for tool in self._tools.values()
        ]

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        logger.info("Cleared all tools from registry")

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools

    def __iter__(self):
        """Iterate over tools."""
        return iter(self._tools.values())


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry.

    Returns:
        The global ToolRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: BaseTool) -> None:
    """Register a tool in the global registry.

    Args:
        tool: The tool to register.
    """
    get_global_registry().register(tool)


def get_tool(name: str) -> BaseTool | None:
    """Get a tool from the global registry.

    Args:
        name: Tool name.

    Returns:
        The tool or None.
    """
    return get_global_registry().get(name)
