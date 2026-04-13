#!/usr/bin/env python
"""Admin script to rerun agents for a topic.

Usage:
    python scripts/admin_rerun_topic.py --topic-id 123 --agent historian
    python scripts/admin_rerun_topic.py --topic-id 123 --agent analyst --force
    python scripts/admin_rerun_topic.py --topic-id 123 --all
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, ".")

from app.bootstrap.logging import get_logger
from app.contracts.dto.editorial import AgentType, RerunAgentDTO, TargetType
from app.editorial.hitl_service import HITLService
from app.storage.db.session import SessionFactory
from app.storage.repositories.editor_action_repository import EditorActionRepository

logger = get_logger(__name__)


async def rerun_agent_for_topic(
    topic_id: int,
    agent_type: AgentType,
    editor_key: str,
    *,
    reason: str | None = None,
    force: bool = False,
) -> dict:
    """Request agent rerun for a topic.

    Args:
        topic_id: Topic ID.
        agent_type: Agent type to rerun.
        editor_key: Editor identifier.
        reason: Reason for rerun.
        force: Force rerun even if recently ran.

    Returns:
        Result dict.
    """
    async with SessionFactory() as session:
        action_repo = EditorActionRepository(session)
        service = HITLService(action_repo=action_repo)

        result = await service.request_rerun_agent(
            RerunAgentDTO(
                target_type=TargetType.TOPIC,
                target_id=topic_id,
                agent_type=agent_type,
                editor_key=editor_key,
                reason=reason,
                force=force,
            )
        )

        await session.commit()

        return {
            "action_id": result.action_id,
            "success": result.success,
            "message": result.message,
        }


async def rerun_all_agents_for_topic(
    topic_id: int,
    editor_key: str,
    *,
    reason: str | None = None,
    force: bool = False,
) -> list[dict]:
    """Request all agents rerun for a topic.

    Args:
        topic_id: Topic ID.
        editor_key: Editor identifier.
        reason: Reason for rerun.
        force: Force rerun.

    Returns:
        List of results.
    """
    results = []
    agents = [AgentType.HISTORIAN, AgentType.ANALYST, AgentType.WRITER, AgentType.REVIEWER]

    for agent in agents:
        result = await rerun_agent_for_topic(
            topic_id=topic_id,
            agent_type=agent,
            editor_key=editor_key,
            reason=reason,
            force=force,
        )
        results.append({
            "agent": agent.value,
            **result,
        })
        print(f"  {agent.value}: {result['message']}")

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rerun agents for a topic"
    )
    parser.add_argument(
        "--topic-id",
        type=int,
        required=True,
        help="Topic ID to rerun agents for",
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["historian", "analyst", "writer", "reviewer"],
        help="Agent type to rerun",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rerun all agents",
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
        help="Reason for rerun",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rerun even if recently ran",
    )

    args = parser.parse_args()

    if not args.agent and not args.all:
        parser.error("Either --agent or --all must be specified")

    print(f"Requesting agent rerun for topic {args.topic_id}")
    print(f"  Editor: {args.editor}")
    print(f"  Reason: {args.reason or 'Not specified'}")
    print(f"  Force: {args.force}")
    print()

    if args.all:
        print("Rerunning all agents...")
        results = asyncio.run(
            rerun_all_agents_for_topic(
                topic_id=args.topic_id,
                editor_key=args.editor,
                reason=args.reason,
                force=args.force,
            )
        )
        print()
        print(f"Completed: {len([r for r in results if r['success']])} / {len(results)} agents queued")
    else:
        agent_type = AgentType(args.agent)
        print(f"Rerunning {agent_type.value}...")
        result = asyncio.run(
            rerun_agent_for_topic(
                topic_id=args.topic_id,
                agent_type=agent_type,
                editor_key=args.editor,
                reason=args.reason,
                force=args.force,
            )
        )
        print(f"  Result: {result['message']}")
        if result['success']:
            print(f"  Action ID: {result['action_id']}")


if __name__ == "__main__":
    main()
