#!/usr/bin/env python
"""Run writer for a topic script.

Usage:
    python scripts/run_writer_for_topic.py <topic_id> [--copy-type feed_card|topic_intro|trend_card]
"""

import argparse
import asyncio
import json


async def main(topic_id: int, copy_type: str) -> None:
    """Run writer for a topic.

    Args:
        topic_id: Topic ID.
        copy_type: Type of copy to generate.
    """
    from app.agents.writer.schemas import CopyType
    from app.agents.writer.service import WriterService

    print(f"Running writer for topic {topic_id}, copy type: {copy_type}")

    # Map string to enum
    copy_type_enum = CopyType(copy_type)

    # Create service
    writer_service = WriterService()

    # Run writer based on copy type
    if copy_type_enum == CopyType.FEED_CARD:
        output, meta = await writer_service.write_feed_card(topic_id)
    elif copy_type_enum == CopyType.TOPIC_INTRO:
        output, meta = await writer_service.write_topic_intro(topic_id)
    elif copy_type_enum == CopyType.TREND_CARD:
        output, meta = await writer_service.write_trend_card(topic_id)
    else:
        print(f"Unsupported copy type: {copy_type}")
        return

    if output:
        print(f"\n=== Writer Output ({copy_type}) ===")
        print(json.dumps(output.model_dump(), indent=2, default=str))
    else:
        print("Writer did not produce output (LLM not configured)")
        print(f"Metadata: {meta}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run writer for a topic")
    parser.add_argument("topic_id", type=int, help="Topic ID")
    parser.add_argument(
        "--copy-type",
        type=str,
        choices=["feed_card", "topic_intro", "trend_card", "report_section"],
        default="topic_intro",
        help="Type of copy to generate",
    )
    args = parser.parse_args()

    asyncio.run(main(args.topic_id, args.copy_type))
