"""TrendHunter Agent module.

The TrendHunter Agent identifies emerging trends and
evaluates topic momentum.
"""

from app.agents.trend_hunter.schemas import (
    TrendHunterInput,
    TrendHunterOutput,
    TrendStage,
)

__all__ = [
    "TrendHunterInput",
    "TrendHunterOutput",
    "TrendStage",
]
