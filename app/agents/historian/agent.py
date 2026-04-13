"""Historian Agent implementation.

The Historian Agent provides historical context and analysis for topics,
determining whether they are new, evolving, recurring, or milestone events.
"""

from typing import Any

from app.agents.base import AgentConfig, BaseAgent
from app.agents.historian.input_builder import HistorianInputBuilder
from app.agents.historian.schemas import HistorianInput, HistorianOutput
from app.agent_runtime.tools.base import BaseTool
from app.agent_runtime.tools.history_tools import get_historian_tools
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class HistorianAgent(BaseAgent[HistorianOutput]):
    """Agent for historical analysis of topics.

    Analyzes topics to determine:
    - When the topic first appeared
    - How it has evolved over time
    - What's new in the current coverage
    - Similar past topics
    - Important background context
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        retrieval_service: Any = None,
    ) -> None:
        """Initialize the Historian Agent.

        Args:
            config: Agent configuration.
            retrieval_service: Memory retrieval service for tools.
        """
        config = config or AgentConfig(
            max_steps=8,
            temperature=0.3,  # Lower temperature for factual analysis
            enable_tools=True,
            prompt_version="v1",
        )
        super().__init__(config=config)
        self._retrieval_service = retrieval_service
        self._input_builder = HistorianInputBuilder()

    @property
    def name(self) -> str:
        """Unique name of the agent."""
        return "historian"

    @property
    def prompt_key(self) -> str:
        """Key for prompt template lookup."""
        return "historian"

    @property
    def output_schema(self) -> type[HistorianOutput]:
        """Pydantic model class for structured output."""
        return HistorianOutput

    def build_input(self, **kwargs: Any) -> str:
        """Build input message for the agent.

        Args:
            **kwargs: Should contain 'historian_input' (HistorianInput).

        Returns:
            Formatted input message.
        """
        historian_input: HistorianInput | None = kwargs.get("historian_input")

        if historian_input is None:
            raise ValueError("historian_input is required")

        # Build context string
        context = self._input_builder.build_prompt_context(historian_input)

        return f"""Please analyze the following topic and provide historical context.

{context}

Based on the above information, provide a comprehensive historical analysis including:
1. When this topic first appeared
2. Its historical status (new, evolving, recurring, or milestone)
3. Current lifecycle stage
4. A summary of its history
5. What's new or different this time
6. Any similar past topics
7. Important background context

Output your analysis as a JSON object matching the expected schema."""

    def build_tools(self) -> list[BaseTool]:
        """Build tools available to the agent.

        Returns:
            List of Historian tools.
        """
        tools = get_historian_tools()

        # Inject retrieval service into tools
        if self._retrieval_service:
            for tool in tools:
                setattr(tool, "_retrieval_service", self._retrieval_service)

        return tools

    def set_retrieval_service(self, service: Any) -> None:
        """Set the retrieval service for tools.

        Args:
            service: Memory retrieval service.
        """
        self._retrieval_service = service

        # Update existing tools if runner already created
        if self._tool_registry:
            for tool in self._tool_registry:
                setattr(tool, "_retrieval_service", service)

    async def analyze_topic(
        self,
        historian_input: HistorianInput,
    ) -> tuple[HistorianOutput | None, Any]:
        """Analyze a topic and return historical context.

        Args:
            historian_input: Prepared input for analysis.

        Returns:
            Tuple of (HistorianOutput or None, RunResult).
        """
        return await self.run_structured(historian_input=historian_input)
