"""Analyst Agent implementation.

The Analyst Agent provides value judgement and analysis for topics,
determining why they matter and to whom.
"""

from typing import Any

from app.agents.base import AgentConfig, BaseAgent
from app.agents.analyst.input_builder import AnalystInputBuilder
from app.agents.analyst.schemas import AnalystInput, AnalystOutput
from app.agent_runtime.tools.base import BaseTool
from app.agent_runtime.tools.analysis_tools import get_analyst_tools
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class AnalystAgent(BaseAgent[AnalystOutput]):
    """Agent for value analysis of topics.

    Analyzes topics to determine:
    - Why the topic matters
    - Who would be interested
    - Current trend stage
    - What to follow up on
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        retrieval_service: Any = None,
    ) -> None:
        """Initialize the Analyst Agent.

        Args:
            config: Agent configuration.
            retrieval_service: Memory retrieval service for tools.
        """
        config = config or AgentConfig(
            max_steps=6,
            temperature=0.4,
            enable_tools=True,
            prompt_version="v1",
        )
        super().__init__(config=config)
        self._retrieval_service = retrieval_service
        self._input_builder = AnalystInputBuilder()

    @property
    def name(self) -> str:
        """Unique name of the agent."""
        return "analyst"

    @property
    def prompt_key(self) -> str:
        """Key for prompt template lookup."""
        return "analyst"

    @property
    def output_schema(self) -> type[AnalystOutput]:
        """Pydantic model class for structured output."""
        return AnalystOutput

    def build_input(self, **kwargs: Any) -> str:
        """Build input message for the agent.

        Args:
            **kwargs: Should contain 'analyst_input' (AnalystInput).

        Returns:
            Formatted input message.
        """
        analyst_input: AnalystInput | None = kwargs.get("analyst_input")

        if analyst_input is None:
            raise ValueError("analyst_input is required")

        # Build context string
        context = self._input_builder.build_prompt_context(analyst_input)

        return f"""Please analyze the following topic and provide value judgement.

{context}

Based on the above information, provide a comprehensive analysis including:
1. Why this topic matters
2. Your overall system judgement
3. Who would be most interested (likely audience)
4. Current trend stage and momentum
5. What to follow up on

Output your analysis as a JSON object matching the expected schema."""

    def build_tools(self) -> list[BaseTool]:
        """Build tools available to the agent.

        Returns:
            List of Analyst tools.
        """
        tools = get_analyst_tools()

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
        analyst_input: AnalystInput,
    ) -> tuple[AnalystOutput | None, Any]:
        """Analyze a topic and return value judgement.

        Args:
            analyst_input: Prepared input for analysis.

        Returns:
            Tuple of (AnalystOutput or None, RunResult).
        """
        return await self.run_structured(analyst_input=analyst_input)
