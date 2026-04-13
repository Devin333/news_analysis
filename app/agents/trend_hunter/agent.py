"""TrendHunter Agent implementation.

The TrendHunter Agent identifies emerging trends and
evaluates topic momentum.
"""

from typing import Any

from app.agents.base import AgentConfig, BaseAgent
from app.agents.trend_hunter.input_builder import TrendHunterInputBuilder
from app.agents.trend_hunter.schemas import TrendHunterInput, TrendHunterOutput
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class TrendHunterAgent(BaseAgent[TrendHunterOutput]):
    """Agent for identifying and evaluating trends.

    Analyzes topics to determine:
    - Whether they are emerging trends
    - Current trend stage
    - Key signals driving the trend
    - What to watch for next
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
    ) -> None:
        """Initialize the TrendHunter Agent.

        Args:
            config: Agent configuration.
        """
        config = config or AgentConfig(
            max_steps=5,
            temperature=0.4,
            enable_tools=False,
            prompt_version="v1",
        )
        super().__init__(config=config)
        self._input_builder = TrendHunterInputBuilder()

    @property
    def name(self) -> str:
        """Unique name of the agent."""
        return "trend_hunter"

    @property
    def prompt_key(self) -> str:
        """Key for prompt template lookup."""
        return "trend_hunter"

    @property
    def output_schema(self) -> type[TrendHunterOutput]:
        """Pydantic model class for structured output."""
        return TrendHunterOutput

    def build_input(self, **kwargs: Any) -> str:
        """Build input message for the agent.

        Args:
            **kwargs: Should contain 'trend_input' (TrendHunterInput).

        Returns:
            Formatted input message.
        """
        trend_input: TrendHunterInput | None = kwargs.get("trend_input")

        if trend_input is None:
            raise ValueError("trend_input is required")

        context = self._input_builder.build_prompt_context(trend_input)

        return f"""Please analyze the following topic for trend signals.

{context}

Based on the metrics and context, determine:
1. Is this an emerging trend?
2. What stage is the trend in?
3. What signals indicate this?
4. Why is this happening now?
5. Should it be featured on the homepage?
6. What should we watch for next?

Output your analysis as a JSON object matching the expected schema."""

    def build_tools(self) -> list:
        """Build tools available to the agent.

        TrendHunter doesn't use tools.

        Returns:
            Empty list.
        """
        return []

    async def analyze_trend(
        self,
        trend_input: TrendHunterInput,
    ) -> tuple[TrendHunterOutput | None, Any]:
        """Analyze a topic for trend signals.

        Args:
            trend_input: Prepared input for analysis.

        Returns:
            Tuple of (TrendHunterOutput or None, RunResult).
        """
        return await self.run_structured(trend_input=trend_input)
