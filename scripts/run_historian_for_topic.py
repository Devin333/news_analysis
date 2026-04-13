#!/usr/bin/env python
"""Script to run historian analysis for a single topic.

Usage:
    python -m app.scripts.run_historian_for_topic --topic-id 123
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime

from app.bootstrap.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def run_historian_for_topic(topic_id: int, save: bool = True) -> dict:
    """Run historian analysis for a topic.

    Args:
        topic_id: ID of the topic to analyze.
        save: Whether to save results to database.

    Returns:
        Result dict with output and metadata.
    """
    from app.agents.historian.service import HistorianService
    from app.memory.retrieval.service import MemoryRetrievalService
    from app.memory.topic_memory.service import TopicMemoryService
    from app.storage.uow import UnitOfWork

    logger.info(f"Running historian for topic {topic_id}")
    start_time = datetime.utcnow()

    # Create services
    uow = UnitOfWork()
    retrieval_service = MemoryRetrievalService(uow=uow)
    historian_service = HistorianService(
        retrieval_service=retrieval_service,
        uow=uow,
    )
    topic_memory_service = TopicMemoryService(uow=uow)

    # Run historian
    output, metadata = await historian_service.run_for_topic(topic_id)

    result = {
        "topic_id": topic_id,
        "success": output is not None,
        "metadata": metadata,
        "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
    }

    if output:
        result["output"] = output.model_dump(mode="json")

        # Validate output
        validation_errors = validate_historian_output(output)
        result["validation_errors"] = validation_errors
        result["is_valid"] = len(validation_errors) == 0

        # Save if requested
        if save:
            saved = await topic_memory_service.update_from_historian(topic_id, output)
            result["saved"] = saved
            logger.info(f"Saved historian output: {saved}")

        # Print summary
        logger.info(f"Historian output for topic {topic_id}:")
        logger.info(f"  Historical status: {output.historical_status}")
        logger.info(f"  Current stage: {output.current_stage}")
        logger.info(f"  Confidence: {output.historical_confidence:.2f}")
        logger.info(f"  Timeline points: {len(output.timeline_points)}")
        logger.info(f"  Similar topics: {len(output.similar_past_topics)}")

        if validation_errors:
            logger.warning(f"Validation errors: {validation_errors}")
    else:
        logger.error(f"Historian analysis failed for topic {topic_id}")
        result["output"] = None
        result["validation_errors"] = ["Analysis failed"]
        result["is_valid"] = False

    return result


def validate_historian_output(output) -> list[str]:
    """Validate historian output for obvious errors.

    Args:
        output: HistorianOutput to validate.

    Returns:
        List of validation error messages.
    """
    errors = []

    # Check first_seen_at is not in the future
    if output.first_seen_at > datetime.utcnow():
        errors.append("first_seen_at is in the future")

    # Check first_seen_at <= last_seen_at
    if output.first_seen_at > output.last_seen_at:
        errors.append("first_seen_at is after last_seen_at")

    # Check confidence is in valid range
    if not 0 <= output.historical_confidence <= 1:
        errors.append(f"historical_confidence out of range: {output.historical_confidence}")

    # Check history_summary is not empty for non-new topics
    if output.historical_status != "new" and not output.history_summary:
        errors.append("history_summary is empty for non-new topic")

    # Check timeline is not empty but history_summary is
    if output.timeline_points and not output.history_summary:
        errors.append("timeline_points present but history_summary is empty")

    # Check what_is_new_this_time is not empty
    if not output.what_is_new_this_time:
        errors.append("what_is_new_this_time is empty")

    return errors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run historian analysis for a topic"
    )
    parser.add_argument(
        "--topic-id",
        type=int,
        required=True,
        help="Topic ID to analyze",
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
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    # Run
    result = asyncio.run(
        run_historian_for_topic(
            topic_id=args.topic_id,
            save=not args.no_save,
        )
    )

    # Output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Result written to {args.output}")
    elif args.verbose:
        print(json.dumps(result, indent=2, default=str))

    # Exit code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
