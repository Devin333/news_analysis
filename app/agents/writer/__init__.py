"""Writer Agent module.

The Writer Agent generates different types of content copy
based on structured inputs from Historian and Analyst.
"""

from app.agents.writer.schemas import (
    CopyType,
    FeedCardCopyDTO,
    ReportSectionCopyDTO,
    TopicIntroCopyDTO,
    TrendCardCopyDTO,
    WriterInput,
    WriterOutput,
)

__all__ = [
    "CopyType",
    "FeedCardCopyDTO",
    "ReportSectionCopyDTO",
    "TopicIntroCopyDTO",
    "TrendCardCopyDTO",
    "WriterInput",
    "WriterOutput",
]
