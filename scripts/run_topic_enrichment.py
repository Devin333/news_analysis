#!/usr/bin/env python
"""Script to run topic enrichment pipeline.

Usage:
    python -m scripts.run_topic_enrichment --topic-id 123
    python -m scripts.run_topic_enrichment --topic-id 123 --historian-only
    python -m scripts.run_topic_enrichment --topic-id 123 --analyst-only
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime

from app.bootstrap.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def run_topic_enrichment(
    topic_id: int,
    run_historian: bool = True,
    run_analyst: bool = True,
    refresh_timeline: bool = True,
    save: bool = True,
) -> dict:
    """Run enrichment pipeline for a topic.

    Args:
        topic_id: ID of the topic to enrich.
        run_historian: Whether to run Historian.
        run_analyst: Whether to run Analyst.
        refresh_timeline: Whether to refresh timeline.
        save: Whether to save results.

    Returns:
        Result dict.
    """
    from app.editorial.topic_enrichment_pipeline import (
        TopicEnrichmentPipeline,
    )
    from app.agents.analyst.service import AnalystService
    from app.agents.historian.service import HistorianService
    from app.editorial.insight_service import InsightService
    from app.memory.topic_memory.service import TopicMemoryService
    from app.storage.uow import UnitOfWork

    logger.info(f"Running enrichment for topic {topic_id}")
    start_time = datetime.utcnow()

    # Create services
    uow = UnitOfWork()
    topic_memory_service = TopicMemoryService(uow=uow)
    insight_service = InsightService(uow=uow)

    historian_service = HistorianService(uow=uow) if run_historian else None
    analyst_service = AnalystService(uow=uow) if run_analyst else None

    # Create pipeline
    pipeline = TopicEnrichmentPipeline(
        historian_service=historian_service,
        analyst_service=analyst_service,
        topic_memory_service=topic_memory_service,
        insight_service=insight_service,
        uow=uow,
    )

    # Run enrichment
    result = await pipeline.enrich_topic(
        topic_id,
        run_historian=run_historian,
        run_analyst=run_analyst,
        refresh_timeline=refresh_timeline,
        save_results=save,
    )

    # Build output
    output = result.to_dict()
    output["duration_ms"] = (datetime.utcnow() - start_time).total_seconds() * 1000

    # Log summary
    if result.success:
        logger.info(f"Enrichment completed for topic {topic_id}")
        if result.historian_output:
            logger.info(f"  Historian: {result.historian_output.historical_status}")
        if result.analyst_output:
            logger.info(f"  Analyst: {result.analyst_output.trend_stage}")
    else:
        logger.warning(f"Enrichment failed for topic {topic_id}: {result.errors}")

    return output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run topic enrichment pipeline"
    )
    parser.add_argument(
        "--topic-id",
        type=int,
        required=True,
        help="Topic ID to enrich",
    )
    parser.add_argument(
        "--historian-only",
        action="store_true",
        help="Only run Historian",
    )
    parser.add_argument(
        "--analyst-only",
        action="store_true",
        help="Only run Analyst",
    )
    parser.add_argument(
        "--no-timeline",
        action="store_true",
        help="Skip timeline refresh",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to database",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for JSON result",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    # Determine what to run
    run_historian = not args.analyst_only
    run_analyst = not args.historian_only

    # Run
    result = asyncio.run(
        run_topic_enrichment(
            topic_id=args.topic_id,
            run_historian=run_historian,
            run_analyst=run_analyst,
            refresh_timeline=not args.no_timeline,
            save=not args.no_save,
        )
    )

    # Output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Result written to {args.output}")
    else:
        print(json.dumps(result, indent=2, default=str))

    # Exit code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
