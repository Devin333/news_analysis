"""Base agent class for business agents.

This module provides the base class that all business agents inherit from.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.bootstrap.logging import get_logger
from app.agent_runtime.runner import AgentRunner, RunConfig, RunResult
from app.agent_runtime.tools.base import BaseTool
from app.agent_runtime.tools.registry import ToolRegistry

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class AgentConfig:
    """Configuration for business agent."""

    max_steps: int = 5
    temperature: float = 0.7
    enable_tools: bool = True
    prompt_version: str = "v1"


class BaseAgent(ABC, Generic[T]):
    """Abstract base class for business agents.

    All business agents must implement:
    - name: Unique agent identifier
    - prompt_key: Key for prompt template lookup
    - output_schema: Pydantic model for structured output
    - build_input: Build input context for the agent
    - build_tools: Build tools available to the agent
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        runner: AgentRunner | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            config: Agent configuration.
            runner: Optional custom runner.
        """
        self._config = config or AgentConfig()
        self._runner = runner
        self._tool_registry: ToolRegistry | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the agent."""
        pass

    @property
    @abstractmethod
    def prompt_key(self) -> str:
        """Key for prompt template lookup."""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> type[T]:
        """Pydantic model class for structured output."""
        pass

    @abstractmethod
    def build_input(self, **kwargs: Any) -> str:
        """Build input message for the agent.

        Args:
            **kwargs: Input parameters.

        Returns:
            Formatted input message.
        """
        pass

    def build_tools(self) -> list[BaseTool]:
        """Build tools available to the agent.

        Override to provide agent-specific tools.

        Returns:
            List of tools.
        """
        return []

    def get_system_prompt(self) -> str:
        """Get system prompt for the agent.

        Returns:
            System prompt string.
        """
        from app.prompts.registry import get_prompt

        prompt = get_prompt(self.prompt_key, version=self._config.prompt_version)
        return prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Default system prompt if none found."""
        return f"""You are {self.name}, an AI assistant.
Analyze the input and provide a structured response.
Always output valid JSON matching the expected schema."""

    def _get_runner(self) -> AgentRunner:
        """Get or create agent runner."""
        if self._runner is None:
            from app.agent_runtime.runner import AgentRunner

            # Build tool registry
            tools = self.build_tools()
            if tools and self._config.enable_tools:
                self._tool_registry = ToolRegistry()
                for tool in tools:
                    self._tool_registry.register(tool)

            self._runner = AgentRunner(
                tool_registry=self._tool_registry,
            )

        return self._runner

    async def run(self, **kwargs: Any) -> RunResult:
        """Run the agent.

        Args:
            **kwargs: Input parameters for build_input.

        Returns:
            RunResult with execution details.
        """
        # Build input
        input_message = self.build_input(**kwargs)

        # Get system prompt
        system_prompt = self.get_system_prompt()

        # Configure run
        run_config = RunConfig(
            max_steps=self._config.max_steps,
            system_prompt=system_prompt,
        )

        # Execute
        runner = self._get_runner()
        result = await runner.run(input_message, config=run_config)

        logger.info(
            f"Agent {self.name} completed: status={result.status}, "
            f"steps={result.total_steps}, duration={result.total_duration_ms:.1f}ms"
        )

        return result

    async def run_structured(self, **kwargs: Any) -> tuple[T | None, RunResult]:
        """Run agent and parse structured output.

        Args:
            **kwargs: Input parameters.

        Returns:
            Tuple of (parsed output or None, run result).
        """
        result = await self.run(**kwargs)

        if not result.success or not result.final_output:
            return None, result

        # Parse output
        try:
            parsed = self._parse_output(result.final_output)
            return parsed, result
        except Exception as e:
            logger.error(f"Failed to parse agent output: {e}")
            return None, result

    def _parse_output(self, output: str) -> T:
        """Parse output into structured format.

        Args:
            output: Raw output string.

        Returns:
            Parsed output model.
        """
        import json

        # Try to extract JSON from output
        output = output.strip()

        # Handle markdown code blocks
        if output.startswith("```"):
            lines = output.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)
            output = "\n".join(json_lines)

        # Parse JSON
        data = json.loads(output)

        # Validate with schema
        return self.output_schema.model_validate(data)
