#!/usr/bin/env python
"""Debug script for search analysis.

Usage:
    python scripts/debug_search.py query <query> [--mode <mode>]
    python scripts/debug_search.py policies
    python scripts/debug_search.py explain <query> <result_id>
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, ".")


async def debug_search_query(query: str, mode: str) -> None:
    """Debug a search query."""
    print(f"\n=== Search Debug: '{query}' ===")
    print(f"Mode: {mode}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()

    from app.contracts.dto.search import SearchMode, SearchQueryDTO

    search_query = SearchQueryDTO(
        query=query,
        mode=SearchMode(mode),
        top_k=20,
        include_explanation=True,
    )

    print("Query Configuration:")
    print(f"  - mode: {search_query.mode.value}")
    print(f"  - top_k: {search_query.top_k}")
    print(f"  - semantic_enabled: {search_query.semantic_enabled}")
    print(f"  - board_filter: {search_query.board_filter}")
    print(f"  - tags: {search_query.tags}")
    print()

    # Show what would happen
    print("Search Flow:")
    if search_query.mode == SearchMode.KEYWORD:
        print("  1. Execute keyword search only")
        print("  2. Apply filters")
        print("  3. Rank results")
    elif search_query.mode == SearchMode.SEMANTIC:
        print("  1. Generate query embedding")
        print("  2. Execute vector similarity search")
        print("  3. Apply min_score filter")
        print("  4. Rank results")
    else:
        print("  1. Execute keyword search")
        print("  2. Generate query embedding")
        print("  3. Execute semantic search")
        print("  4. Merge results (weighted/rrf/interleaved)")
        print("  5. Boost hybrid matches")
        print("  6. Apply filters")
        print("  7. Rank results")
    print()

    print("Note: Connect to database for actual search results.")


async def show_policies() -> None:
    """Show all search policies."""
    print("\n=== Search Policies ===")
    print()

    from app.search.policies import SearchPolicies, SearchPolicyMode

    policies = [
        ("User Search", SearchPolicies.user_search()),
        ("Topic Lookup", SearchPolicies.topic_lookup()),
        ("Entity Lookup", SearchPolicies.entity_lookup()),
        ("Historical Case Lookup", SearchPolicies.historical_case_lookup()),
        ("Agent Retrieval", SearchPolicies.agent_retrieval()),
        ("Similar Content", SearchPolicies.similar_content()),
    ]

    for name, policy in policies:
        print(f"\n{name} ({policy.mode.value})")
        print("-" * 40)
        print(f"  keyword_enabled: {policy.keyword_enabled}")
        print(f"  semantic_enabled: {policy.semantic_enabled}")
        print(f"  keyword_weight: {policy.keyword_weight:.0%}")
        print(f"  semantic_weight: {policy.semantic_weight:.0%}")
        print(f"  min_score: {policy.min_score}")
        print(f"  boost_hybrid: {policy.boost_hybrid}")
        print(f"  merge_strategy: {policy.merge_strategy}")
        print(f"  max_results: {policy.max_results}")
        print(f"  include_explanation: {policy.include_explanation}")


async def explain_result(query: str, result_id: int) -> None:
    """Explain a search result."""
    print(f"\n=== Search Explanation ===")
    print(f"Query: '{query}'")
    print(f"Result ID: {result_id}")
    print()

    from app.contracts.dto.search import (
        SearchContentType,
        SearchQueryDTO,
        SearchResultItemDTO,
    )
    from app.search.explain import SearchExplainer

    # Create mock result for demonstration
    mock_result = SearchResultItemDTO(
        id=result_id,
        content_type=SearchContentType.TOPIC,
        score=0.85,
        title=f"Sample Topic {result_id}",
        summary="This is a sample topic for demonstration.",
        matched_by="hybrid",
        keyword_score=0.8,
        semantic_score=0.9,
        matched_fields=["title", "summary"],
    )

    search_query = SearchQueryDTO(query=query)

    explainer = SearchExplainer()
    explanation = explainer.explain_result(mock_result, search_query)

    print("Explanation:")
    print(f"  Final Score: {explanation.final_score:.3f}")
    print(f"  Semantic Similarity: {explanation.semantic_similarity}")
    print()
    print("  Keyword Matches:")
    for match in explanation.keyword_matches:
        print(f"    - {match['field']}: '{match['term']}'")
    print()
    print("  Score Components:")
    for name, value in explanation.score_components.items():
        print(f"    - {name}: {value:.3f}")
    print()
    print(f"  Explanation: {explanation.explanation_text}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Debug search analysis")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # query command
    query_parser = subparsers.add_parser("query", help="Debug search query")
    query_parser.add_argument("query", help="Search query")
    query_parser.add_argument("--mode", default="hybrid", help="Search mode")

    # policies command
    subparsers.add_parser("policies", help="Show all policies")

    # explain command
    explain_parser = subparsers.add_parser("explain", help="Explain result")
    explain_parser.add_argument("query", help="Search query")
    explain_parser.add_argument("result_id", type=int, help="Result ID")

    args = parser.parse_args()

    if args.command == "query":
        asyncio.run(debug_search_query(args.query, args.mode))
    elif args.command == "policies":
        asyncio.run(show_policies())
    elif args.command == "explain":
        asyncio.run(explain_result(args.query, args.result_id))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
