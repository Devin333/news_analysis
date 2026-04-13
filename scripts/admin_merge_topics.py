#!/usr/bin/env python
"""Admin script to merge topics.

Usage:
    python scripts/admin_merge_topics.py --target 123 --sources 456 789
    python scripts/admin_merge_topics.py --target 123 --sources 456 789 --reason "Duplicate topics"
"""

import argparse
import asyncio
import sys

# Add project root to path
sys.path.insert(0, ".")

from app.bootstrap.logging import get_logger
from app.contracts.dto.editorial import MergeTopicsDTO
from app.editorial.hitl_service import HITLService
from app.storage.db.session import SessionFactory
from app.storage.repositories.editor_action_repository import EditorActionRepository

logger = get_logger(__name__)


async def merge_topics(
    target_topic_id: int,
    source_topic_ids: list[int],
    editor_key: str,
    *,
    reason: str | None = None,
) -> dict:
    """Merge topics into target.

    Args:
        target_topic_id: Target topic ID.
        source_topic_ids: Source topic IDs to merge.
        editor_key: Editor identifier.
        reason: Reason for merge.

    Returns:
        Result dict.
    """
    async with SessionFactory() as session:
        action_repo = EditorActionRepository(session)
        service = HITLService(action_repo=action_repo)

        result = await service.merge_topics_manual(
            MergeTopicsDTO(
                source_topic_ids=source_topic_ids,
                target_topic_id=target_topic_id,
                editor_key=editor_key,
                reason=reason,
            )
        )

        await session.commit()

        return {
            "action_id": result.action_id,
            "success": result.success,
            "message": result.message,
            "affected_ids": result.affected_ids,
            "changes": result.changes,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Merge topics into a target topic"
    )
    parser.add_argument(
        "--target",
        type=int,
        required=True,
        help="Target topic ID to merge into",
    )
    parser.add_argument(
        "--sources",
        type=int,
        nargs="+",
        required=True,
        help="Source topic IDs to merge from",
    )
    parser.add_argument(
        "--editor",
        type=str,
        default="admin_script",
        help="Editor key (default: admin_script)",
    )
    parser.add_argument(
        "--reason",
        type=str,
        help="Reason for merge",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    # Filter out target from sources if accidentally included
    source_ids = [s for s in args.sources if s != args.target]

    if not source_ids:
        print("Error: No valid source topics to merge (target cannot be in sources)")
        sys.exit(1)

    print(f"Merge Topics Operation")
    print(f"=" * 40)
    print(f"Target topic: {args.target}")
    print(f"Source topics: {source_ids}")
    print(f"Editor: {args.editor}")
    print(f"Reason: {args.reason or 'Not specified'}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would merge the following:")
        print(f"  - Topics {source_ids} -> Topic {args.target}")
        print("  - All items from source topics would be moved to target")
        print("  - Source topics would be marked as merged")
        return

    # Confirm
    confirm = input(f"Merge {len(source_ids)} topics into topic {args.target}? [y/N] ")
    if confirm.lower() != "y":
        print("Cancelled")
        return

    print()
    print("Merging topics...")
    result = asyncio.run(
        merge_topics(
            target_topic_id=args.target,
            source_topic_ids=source_ids,
            editor_key=args.editor,
            reason=args.reason,
        )
    )

    print()
    if result["success"]:
        print(f"Success: {result['message']}")
        print(f"Action ID: {result['action_id']}")
        print(f"Affected topics: {result['affected_ids']}")
    else:
        print(f"Failed: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
