"""Script to rebuild topic snapshots.

Usage:
    python -m app.scripts.rebuild_topic_snapshots [--limit N] [--topic-id ID]
"""

import argparse
import asyncio
import sys

from app.bootstrap.logging import get_logger, setup_logging
from app.memory.service import MemoryService
from app.memory.topic_memory.snapshot_builder import TopicSnapshotBuilder
from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


async def rebuild_snapshots(
    limit: int = 100,
    topic_id: int | None = None,
) -> int:
    """Rebuild topic snapshots.

    Args:
        limit: Maximum number of topics to process.
        topic_id: Optional specific topic ID to rebuild.

    Returns:
        Number of snapshots created.
    """
    created_count = 0

    async with UnitOfWork() as uow:
        # Create memory service
        memory_service = MemoryService.from_uow(uow)

        # Create snapshot builder
        builder = TopicSnapshotBuilder(
            topic_repo=uow.topics,
            item_repo=uow.normalized_items,
        )

        if topic_id:
            # Rebuild single topic
            topic_ids = [topic_id]
        else:
            # Get recent topics
            topics = await uow.topics.list_recent(limit=limit)
            topic_ids = [t.id for t in topics]

        logger.info(f"Rebuilding snapshots for {len(topic_ids)} topics")

        for tid in topic_ids:
            try:
                # Build snapshot
                snapshot_data = await builder.build_snapshot(tid)
                if snapshot_data is None:
                    logger.warning(f"Skipping topic {tid}: no data")
                    continue

                # Save snapshot
                snapshot = await memory_service.create_topic_snapshot(tid, snapshot_data)
                if snapshot:
                    created_count += 1
                    logger.info(f"Created snapshot for topic {tid}")
                else:
                    logger.warning(f"Failed to save snapshot for topic {tid}")

            except Exception as e:
                logger.error(f"Error processing topic {tid}: {e}")
                continue

    return created_count


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Rebuild topic snapshots")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of topics to process",
    )
    parser.add_argument(
        "--topic-id",
        type=int,
        default=None,
        help="Specific topic ID to rebuild",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(level="DEBUG" if args.verbose else "INFO")

    logger.info("Starting topic snapshot rebuild")

    # Run async
    count = asyncio.run(rebuild_snapshots(
        limit=args.limit,
        topic_id=args.topic_id,
    ))

    logger.info(f"Completed: created {count} snapshots")
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
