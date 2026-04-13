#!/usr/bin/env python
"""Script to rebuild historical context for multiple topics.

Usage:
    python -m scripts.rebuild_historical_context --limit 10
    python -m scripts.rebuild_historical_context --topic-ids 1,2,3
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Any

from app.bootstrap.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def rebuild_historical_context(
    topic_ids: list[int] | None = None,
    limit: int = 10,
    skip_existing: bool = True,
    save: bool = True,
) -> dict[str, Any]:
    """Rebuild historical context for topics.

    Args:
        topic_ids: Specific topic IDs to process.
        limit: Maximum topics to process if topic_ids not specified.
        skip_existing: Skip topics that already have historian output.
        save: Whether to save results.

    Returns:
        Summary of results.
    """
    from app.agents.historian.service import HistorianService
    from app.memory.retrieval.service import MemoryRetrievalService
    from app.memory.topic_memory.service import TopicMemoryService
    from app.storage.uow import UnitOfWork

    logger.info("Starting historical context rebuild")
    start_time = datetime.utcnow()

    # Get topics to process
    uow = UnitOfWork()

    if topic_ids is None:
        async with uow:
            topics = await uow.topics.list_recent(limit=limit)
            topic_ids = [t.id for t in topics]

    logger.info(f"Processing {len(topic_ids)} topics")

    # Create services
    retrieval_service = MemoryRetrievalService(uow=uow)
    historian_service = HistorianService(
        retrieval_service=retrieval_service,
        uow=uow,
    )
    topic_memory_service = TopicMemoryService(uow=uow)

    # Process each topic
    results = {
        "total": len(topic_ids),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "topics": [],
    }

    for topic_id in topic_ids:
        topic_result = {
            "topic_id": topic_id,
            "status": "pending",
        }

        try:
            # Check if already has historian output
            if skip_existing:
                existing = await topic_memory_service.get_historian_output(topic_id)
                if existing:
                    logger.info(f"Skipping topic {topic_id} - already has historian output")
                    topic_result["status"] = "skipped"
                    results["skipped"] += 1
                    results["topics"].append(topic_result)
                    continue

            # Run historian
            output, metadata = await historian_service.run_for_topic(topic_id)

            if output:
                topic_result["status"] = "success"
                topic_result["historical_status"] = output.historical_status.value
                topic_result["confidence"] = output.historical_confidence

                # Save if requested
                if save:
                    saved = await topic_memory_service.update_from_historian(
                        topic_id, output
                    )
                    topic_result["saved"] = saved

                results["success"] += 1
                logger.info(
                    f"Topic {topic_id}: {output.historical_status.value} "
                    f"(confidence={output.historical_confidence:.2f})"
                )
            else:
                topic_result["status"] = "failed"
                topic_result["error"] = metadata.get("error", "Unknown error")
                results["failed"] += 1
                logger.warning(f"Topic {topic_id}: failed - {topic_result['error']}")

        except Exception as e:
            topic_result["status"] = "error"
            topic_result["error"] = str(e)
            results["failed"] += 1
            logger.error(f"Topic {topic_id}: error - {e}")

        results["topics"].append(topic_result)

    # Summary
    end_time = datetime.utcnow()
    results["duration_ms"] = (end_time - start_time).total_seconds() * 1000
    results["started_at"] = start_time.isoformat()
    results["completed_at"] = end_time.isoformat()

    logger.info(
        f"Rebuild complete: {results['success']} success, "
        f"{results['failed']} failed, {results['skipped']} skipped"
    )

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rebuild historical context for topics"
    )
    parser.add_argument(
        "--topic-ids",
        type=str,
        help="Comma-separated list of topic IDs",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum topics to process (default: 10)",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Process topics even if they have existing historian output",
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

    # Parse topic IDs
    topic_ids = None
    if args.topic_ids:
        topic_ids = [int(x.strip()) for x in args.topic_ids.split(",")]

    # Run
    result = asyncio.run(
        rebuild_historical_context(
            topic_ids=topic_ids,
            limit=args.limit,
            skip_existing=not args.no_skip_existing,
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
    sys.exit(0 if result["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
