#!/usr/bin/env python
"""Run review for a topic script.

Usage:
    python scripts/run_review_for_topic.py <topic_id> [--copy-type feed_card|topic_intro|trend_card]
"""

import argparse
import asyncio
import json


async def main(topic_id: int, copy_type: str) -> None:
    """Run review for a topic.

    Args:
        topic_id: Topic ID.
        copy_type: Type of copy to review.
    """
    from app.agents.reviewer.service import ReviewerService
    from app.agents.writer.schemas import CopyType
    from app.agents.writer.service import WriterService

    print(f"Running writer then reviewer for topic {topic_id}, copy type: {copy_type}")

    # Map string to enum
    copy_type_enum = CopyType(copy_type)

    # Create services
    writer_service = WriterService()
    reviewer_service = ReviewerService()

    # First generate copy
    print("\n--- Step 1: Generate Copy ---")
    if copy_type_enum == CopyType.FEED_CARD:
        writer_output, writer_meta = await writer_service.write_feed_card(topic_id)
    elif copy_type_enum == CopyType.TOPIC_INTRO:
        writer_output, writer_meta = await writer_service.write_topic_intro(topic_id)
    elif copy_type_enum == CopyType.TREND_CARD:
        writer_output, writer_meta = await writer_service.write_trend_card(topic_id)
    else:
        print(f"Unsupported copy type: {copy_type}")
        return

    if writer_output is None:
        print("Writer did not produce output (LLM not configured)")
        print("Using mock copy for review demonstration...")
        # Create mock copy for demonstration
        mock_copy = {
            "title": "Sample Topic Title",
            "short_summary": "This is a sample summary for demonstration.",
            "why_it_matters_short": "Important for testing the review pipeline.",
        }
    else:
        print("Writer output generated successfully")
        mock_copy = writer_output.model_dump()

    # Then review
    print("\n--- Step 2: Review Copy ---")
    if copy_type_enum == CopyType.FEED_CARD:
        review_output, review_meta = await reviewer_service.review_feed_card(
            topic_id, mock_copy
        )
    elif copy_type_enum == CopyType.TOPIC_INTRO:
        review_output, review_meta = await reviewer_service.review_topic_intro(
            topic_id, mock_copy
        )
    elif copy_type_enum == CopyType.TREND_CARD:
        review_output, review_meta = await reviewer_service.review_trend_card(
            topic_id, mock_copy
        )
    else:
        review_output = None
        review_meta = {}

    if review_output:
        print(f"\n=== Review Output ===")
        print(f"Status: {review_output.review_status}")
        print(f"Confidence: {review_output.confidence}")
        if review_output.issues:
            print(f"\nIssues ({len(review_output.issues)}):")
            for issue in review_output.issues:
                print(f"  - [{issue.severity}] {issue.issue_type}: {issue.description}")
        if review_output.revision_hints:
            print(f"\nRevision Hints:")
            for hint in review_output.revision_hints:
                print(f"  - {hint}")
        print(f"\nFull output:")
        print(json.dumps(review_output.model_dump(), indent=2, default=str))
    else:
        print("Reviewer did not produce output (LLM not configured)")
        print(f"Metadata: {review_meta}")

    # Run rule-based validators
    print("\n--- Step 3: Rule-based Validation ---")
    from app.editorial.validators.copy_guard import CopyGuard
    from app.editorial.validators.fact_guard import FactGuard

    copy_guard = CopyGuard()
    fact_guard = FactGuard()

    copy_issues = copy_guard.validate(mock_copy, copy_type)
    fact_issues = fact_guard.validate(mock_copy)

    print(f"\nCopy Guard Issues ({len(copy_issues)}):")
    for issue in copy_issues:
        print(f"  - [{issue.severity}] {issue.issue_type}: {issue.description}")

    print(f"\nFact Guard Issues ({len(fact_issues)}):")
    for issue in fact_issues:
        print(f"  - [{issue.severity}] {issue.issue_type}: {issue.description}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run review for a topic")
    parser.add_argument("topic_id", type=int, help="Topic ID")
    parser.add_argument(
        "--copy-type",
        type=str,
        choices=["feed_card", "topic_intro", "trend_card"],
        default="topic_intro",
        help="Type of copy to review",
    )
    args = parser.parse_args()

    asyncio.run(main(args.topic_id, args.copy_type))
