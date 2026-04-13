"""ReportEditor Agent implementation.

The ReportEditor Agent generates structured reports from topic data.
"""

from typing import Any

from app.agents.base import AgentConfig, BaseAgent
from app.agents.report_editor.input_builder import ReportEditorInputBuilder
from app.agents.report_editor.schemas import ReportEditorInput, ReportEditorOutput
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class ReportEditorAgent(BaseAgent[ReportEditorOutput]):
    """Agent for generating intelligence reports.

    Acts as the "Editor-in-Chief" to:
    - Organize topics into sections
    - Write executive summaries
    - Provide editorial conclusions
    - Identify watch items
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
    ) -> None:
        """Initialize the ReportEditor Agent.

        Args:
            config: Agent configuration.
        """
        config = config or AgentConfig(
            max_steps=5,
            temperature=0.5,
            enable_tools=False,
            prompt_version="v1",
        )
        super().__init__(config=config)
        self._input_builder = ReportEditorInputBuilder()

    @property
    def name(self) -> str:
        """Unique name of the agent."""
        return "report_editor"

    @property
    def prompt_key(self) -> str:
        """Key for prompt template lookup."""
        return "report_editor"

    @property
    def output_schema(self) -> type[ReportEditorOutput]:
        """Pydantic model class for structured output."""
        return ReportEditorOutput

    def build_input(self, **kwargs: Any) -> str:
        """Build input message for the agent.

        Args:
            **kwargs: Should contain 'report_input' (ReportEditorInput).

        Returns:
            Formatted input message.
        """
        report_input: ReportEditorInput | None = kwargs.get("report_input")

        if report_input is None:
            raise ValueError("report_input is required")

        context = self._input_builder.build_prompt_context(report_input)

        report_type = report_input.report_type.value
        date_str = report_input.report_date.strftime("%Y-%m-%d")

        return f"""Please generate a {report_type} intelligence report for {date_str}.

{context}

Based on the topics and signals provided, create a comprehensive report with:
1. An engaging title
2. An executive summary (2-3 paragraphs)
3. Key highlights (3-5 items)
4. Organized sections with key points
5. An editorial conclusion
6. Items to watch next

Output your report as a JSON object matching the expected schema."""

    def build_tools(self) -> list:
        """Build tools available to the agent.

        ReportEditor doesn't use tools.

        Returns:
            Empty list.
        """
        return []

    async def generate_report(
        self,
        report_input: ReportEditorInput,
    ) -> tuple[ReportEditorOutput | None, Any]:
        """Generate a report.

        Args:
            report_input: Prepared input for report generation.

        Returns:
            Tuple of (ReportEditorOutput or None, metadata).
        """
        return await self.run_structured(report_input=report_input)

    async def generate_daily_report(
        self,
        date: Any,
        topics: list[dict[str, Any]],
        *,
        trend_signals: list[dict[str, Any]] | None = None,
        insights: list[str] | None = None,
        previous_report: dict[str, Any] | None = None,
    ) -> tuple[ReportEditorOutput | None, Any]:
        """Generate a daily report.

        Args:
            date: Report date.
            topics: List of topic dicts.
            trend_signals: Optional trend signals.
            insights: Optional key insights.
            previous_report: Optional previous report.

        Returns:
            Tuple of (ReportEditorOutput or None, metadata).
        """
        report_input = self._input_builder.build_daily_input(
            date,
            topics=topics,
            trend_signals=trend_signals,
            insights=insights,
            previous_report=previous_report,
        )
        return await self.generate_report(report_input)

    async def generate_weekly_report(
        self,
        start_date: Any,
        end_date: Any,
        topics: list[dict[str, Any]],
        *,
        trend_signals: list[dict[str, Any]] | None = None,
        insights: list[str] | None = None,
        daily_reports: list[dict[str, Any]] | None = None,
        previous_weekly: dict[str, Any] | None = None,
    ) -> tuple[ReportEditorOutput | None, Any]:
        """Generate a weekly report.

        Args:
            start_date: Week start date.
            end_date: Week end date.
            topics: List of topic dicts.
            trend_signals: Optional trend signals.
            insights: Optional key insights.
            daily_reports: Optional daily reports from the week.
            previous_weekly: Optional previous weekly report.

        Returns:
            Tuple of (ReportEditorOutput or None, metadata).
        """
        report_input = self._input_builder.build_weekly_input(
            start_date,
            end_date,
            topics=topics,
            trend_signals=trend_signals,
            insights=insights,
            daily_reports=daily_reports,
            previous_weekly=previous_weekly,
        )
        return await self.generate_report(report_input)
