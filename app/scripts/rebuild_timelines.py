"""Script to rebuild topic timelines.

Usage:
    python -m app.scripts.rebuild_timelines [--limit N] [--topic-id ID]
"""

import argparse
import asyncio
import sys

from app.bootstrap.logging import get_logger, setup_logging
from app.memory.repositories.timeline_repository import TimelineRepository
from app.memory.timeline.service import TimelineService
from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
from app.storage.repositories.topic_repository import TopicRepository
from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


async def rebuild_timelines(
    limit: int = 100,
    topic_id: int | None = None,
) -> int:
    """Rebuild topic timelines.

    Args:
        limit: Maximum number of topics to process.
        topic_id: Optional specific topic ID to rebuild.

    Returns:
        Number of timelines rebuilt.
    """
    rebuilt_count = 0

    async with UnitOfWork() as uow:
        # Create repositories
        timeline_repo = TimelineRepository(uow.session)
        topic_repo = uow.topics
        item_repo = uow.normalized_items

        # Create timeline service
        service = TimelineService(
            timeline_repo=timeline_repo,
            topic_repo=topic_repo,
            item_repo=item_repo,
        )

        if topic_id:
            # Rebuild single topic
            topic_ids = [topic_id]
        else:
            # Get recent topics
            topics = await topic_repo.list_recent(limit=limit)
            topic_ids = [t.id for t in topics]

        logger.info(f"Rebuilding timelines for {len(topic_ids)} topics")

        for tid in topic_ids:
            try:
                events = await service.refresh_topic_timeline(tid)
                if events:
                    rebuilt_count += 1
                    logger.info(f"Rebuilt timeline for topic {tid}: {len(events)} events")
                else:
                    logger.warning(f"No events generated for topic {tid}")

            except Exception as e:
                logger.error(f"Error processing topic {tid}: {e}")
                continue

    return rebuilt_count


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Rebuild topic timelines")
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
    setup_logging()

    logger.info("Starting timeline rebuild")

    # Run async
    count = asyncio.run(rebuild_timelines(
        limit=args.limit,
        topic_id=args.topic_id,
    ))

    logger.info(f"Completed: rebuilt {count} timelines")
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
