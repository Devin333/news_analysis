"""Writer Agent implementation.

The Writer Agent generates different types of content copy
based on structured inputs from Historian and Analyst.
"""

from typing import Any

from app.agents.base import AgentConfig, BaseAgent
from app.agents.writer.context_policy import WriterContextPolicy, get_context_policy
from app.agents.writer.input_builder import WriterInputBuilder
from app.agents.writer.schemas import (
    CopyType,
    FeedCardCopyDTO,
    ReportSectionCopyDTO,
    TopicIntroCopyDTO,
    TrendCardCopyDTO,
    WriterInput,
    WriterOutput,
)
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


# Output schema mapping
OUTPUT_SCHEMAS: dict[CopyType, type] = {
    CopyType.FEED_CARD: FeedCardCopyDTO,
    CopyType.TOPIC_INTRO: TopicIntroCopyDTO,
    CopyType.TREND_CARD: TrendCardCopyDTO,
    CopyType.REPORT_SECTION: ReportSectionCopyDTO,
}


class WriterAgent(BaseAgent[WriterOutput]):
    """Agent for generating content copy.

    Generates different types of copy based on the copy_type:
    - feed_card: Short, punchy content for feed views
    - topic_intro: Comprehensive intro for topic pages
    - trend_card: Trend-focused content for trend pages
    - report_section: Section content for reports
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        copy_type: CopyType = CopyType.FEED_CARD,
    ) -> None:
        """Initialize the Writer Agent.

        Args:
            config: Agent configuration.
            copy_type: Type of copy to generate.
        """
        config = config or AgentConfig(
            max_steps=4,
            temperature=0.7,  # Slightly higher for creative writing
            enable_tools=False,  # Writer doesn't need tools
            prompt_version="v1",
        )
        super().__init__(config=config)
        self._copy_type = copy_type
        self._input_builder = WriterInputBuilder()
        self._context_policy = get_context_policy(copy_type)

    @property
    def name(self) -> str:
        """Unique name of the agent."""
        return f"writer_{self._copy_type.value}"

    @property
    def prompt_key(self) -> str:
        """Key for prompt template lookup."""
        return f"writer_{self._copy_type.value}"

    @property
    def output_schema(self) -> type[WriterOutput]:
        """Pydantic model class for structured output."""
        return WriterOutput

    @property
    def copy_type(self) -> CopyType:
        """Get the copy type."""
        return self._copy_type

    def set_copy_type(self, copy_type: CopyType) -> None:
        """Set the copy type.

        Args:
            copy_type: New copy type.
        """
        self._copy_type = copy_type
        self._context_policy = get_context_policy(copy_type)

    def build_input(self, **kwargs: Any) -> str:
        """Build input message for the agent.

        Args:
            **kwargs: Should contain 'writer_input' (WriterInput).

        Returns:
            Formatted input message.
        """
        writer_input: WriterInput | None = kwargs.get("writer_input")

        if writer_input is None:
            raise ValueError("writer_input is required")

        # Build context string
        context = self._input_builder.build_prompt_context(writer_input)

        # Get output schema for this copy type
        output_schema = OUTPUT_SCHEMAS.get(self._copy_type, FeedCardCopyDTO)
        schema_fields = list(output_schema.model_fields.keys())

        return f"""Please generate {self._copy_type.value} copy for the following topic.

{context}

Generate content with the following fields:
{', '.join(schema_fields)}

Rules:
1. Base ALL content on the provided input - DO NOT invent facts
2. DO NOT contradict the Historian's historical analysis
3. DO NOT contradict the Analyst's judgements
4. Keep language professional but accessible
5. Be specific and concrete - avoid vague generalizations

Output your content as a JSON object matching the expected schema."""

    def build_tools(self) -> list:
        """Build tools available to the agent.

        Writer doesn't use tools - it generates content directly.

        Returns:
            Empty list.
        """
        return []

    async def write(
        self,
        writer_input: WriterInput,
    ) -> tuple[WriterOutput | None, Any]:
        """Generate copy for the given input.

        Args:
            writer_input: Prepared input for writing.

        Returns:
            Tuple of (WriterOutput or None, RunResult).
        """
        # Ensure copy type matches
        if writer_input.copy_type != self._copy_type:
            self.set_copy_type(writer_input.copy_type)

        # Run the agent
        result, meta = await self.run_structured(writer_input=writer_input)

        if result is None:
            return None, meta

        # Wrap in WriterOutput if needed
        if isinstance(result, WriterOutput):
            return result, meta

        # If we got a raw copy DTO, wrap it
        output = WriterOutput(
            copy_type=self._copy_type,
            topic_id=writer_input.topic_id,
        )

        if self._copy_type == CopyType.FEED_CARD and isinstance(result, FeedCardCopyDTO):
            output.feed_card = result
        elif self._copy_type == CopyType.TOPIC_INTRO and isinstance(result, TopicIntroCopyDTO):
            output.topic_intro = result
        elif self._copy_type == CopyType.TREND_CARD and isinstance(result, TrendCardCopyDTO):
            output.trend_card = result
        elif self._copy_type == CopyType.REPORT_SECTION and isinstance(result, ReportSectionCopyDTO):
            output.report_section = result

        return output, meta


def create_writer_agent(copy_type: CopyType) -> WriterAgent:
    """Create a Writer Agent for a specific copy type.

    Args:
        copy_type: Type of copy to generate.

    Returns:
        Configured WriterAgent.
    """
    return WriterAgent(copy_type=copy_type)
