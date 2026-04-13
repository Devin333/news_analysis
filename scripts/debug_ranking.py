#!/usr/bin/env python
"""Debug script for ranking analysis.

Usage:
    python scripts/debug_ranking.py topic <topic_id> [--context <context>]
    python scripts/debug_ranking.py compare <topic_ids> [--context <context>]
    python scripts/debug_ranking.py features <topic_id>
    python scripts/debug_ranking.py strategies
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, ".")


async def debug_topic_ranking(topic_id: int, context_name: str) -> None:
    """Debug ranking for a single topic."""
    print(f"\n=== Ranking Debug: Topic {topic_id} ===")
    print(f"Context: {context_name}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()

    # Import here to avoid circular imports
    from app.contracts.dto.ranking import RankingContextDTO

    context = RankingContextDTO(
        context_name=context_name,
        time_window_hours=24,
        max_results=50,
    )

    print("Context Configuration:")
    print(f"  - time_window_hours: {context.time_window_hours}")
    print(f"  - max_results: {context.max_results}")
    print(f"  - include_unreviewed: {context.include_unreviewed}")
    print()

    # Note: In production, this would use actual database connection
    print("Note: This is a debug script. Connect to database for real data.")
    print()

    # Show strategy weights
    from app.ranking.strategies.news_ranking import NewsRankingStrategy
    from app.ranking.strategies.tech_ranking import TechRankingStrategy
    from app.ranking.strategies.homepage_ranking import HomepageRankingStrategy
    from app.ranking.strategies.trend_ranking import TrendRankingStrategy

    strategies = {
        "news_feed": NewsRankingStrategy(),
        "tech_feed": TechRankingStrategy(),
        "homepage": HomepageRankingStrategy(),
        "trend": TrendRankingStrategy(),
    }

    if context_name in strategies:
        strategy = strategies[context_name]
        weights = strategy.get_weights(context)
        print(f"Strategy: {strategy.strategy_name}")
        print("Weights:")
        for name, weight in sorted(weights.items(), key=lambda x: -x[1]):
            print(f"  - {name}: {weight:.0%}")
    else:
        print(f"Unknown context: {context_name}")
        print(f"Available contexts: {list(strategies.keys())}")


async def compare_topics(topic_ids: list[int], context_name: str) -> None:
    """Compare rankings for multiple topics."""
    print(f"\n=== Ranking Comparison ===")
    print(f"Topics: {topic_ids}")
    print(f"Context: {context_name}")
    print()

    from app.contracts.dto.ranking import RankingContextDTO, RankingFeatureDTO
    from app.ranking.strategies.news_ranking import NewsRankingStrategy

    context = RankingContextDTO(
        context_name=context_name,
        time_window_hours=24,
        max_results=50,
    )

    strategy = NewsRankingStrategy()

    # Create mock features for comparison
    print("Mock Feature Comparison:")
    print("-" * 60)

    for i, topic_id in enumerate(topic_ids):
        # Create varying features for demonstration
        features = RankingFeatureDTO(
            topic_id=topic_id,
            recency_score=0.9 - i * 0.2,
            source_diversity_score=0.5 + i * 0.1,
            trend_signal_score=0.3 + i * 0.15,
            review_passed=True,
            review_pass_bonus=1.0,
            item_count=5 + i,
            source_count=3 + i,
        )

        score = strategy.score_topic(topic_id, features, context)

        print(f"\nTopic {topic_id}:")
        print(f"  Final Score: {score.final_score:.3f}")
        print(f"  Top Factors: {', '.join(score.top_factors)}")
        print(f"  Component Scores:")
        for name, value in sorted(score.component_scores.items(), key=lambda x: -x[1]):
            if value > 0:
                print(f"    - {name}: {value:.3f}")


async def show_features(topic_id: int) -> None:
    """Show all features for a topic."""
    print(f"\n=== Features for Topic {topic_id} ===")
    print()

    from app.contracts.dto.ranking import RankingFeatureDTO

    # Show feature schema
    print("Feature Schema:")
    print("-" * 40)

    feature_descriptions = {
        "recency_score": "Time-based freshness (0-1)",
        "stale_penalty": "Penalty for old content (0-1)",
        "source_authority_score": "Source credibility (0-1)",
        "source_diversity_score": "Number of unique sources (0-1)",
        "trusted_source_score": "Ratio of trusted sources (0-1)",
        "topic_heat_score": "Topic engagement/heat (0-1)",
        "topic_size_score": "Number of items (0-1)",
        "item_count": "Raw item count",
        "source_count": "Raw source count",
        "trend_score": "Base trend score (0-1)",
        "trend_signal_score": "Trend signal strength (0-1)",
        "insight_confidence": "Analyst confidence (0-1)",
        "analyst_importance_score": "Analyst importance rating (0-1)",
        "historian_novelty_score": "Historian novelty rating (0-1)",
        "review_passed": "Whether review passed (bool)",
        "review_pass_bonus": "Bonus for passing review (0-1)",
        "board_weight": "Board relevance multiplier",
        "homepage_candidate_score": "Homepage suitability (0-1)",
    }

    for name, desc in feature_descriptions.items():
        print(f"  {name}: {desc}")


async def show_strategies() -> None:
    """Show all available strategies."""
    print("\n=== Available Ranking Strategies ===")
    print()

    from app.contracts.dto.ranking import RankingContextDTO
    from app.ranking.strategies.news_ranking import NewsRankingStrategy, BoardNewsRankingStrategy
    from app.ranking.strategies.tech_ranking import TechRankingStrategy, DeepTechRankingStrategy, EngineeringRankingStrategy
    from app.ranking.strategies.homepage_ranking import HomepageRankingStrategy, DiversifiedHomepageStrategy
    from app.ranking.strategies.trend_ranking import TrendRankingStrategy, EmergingTrendStrategy, HotTrendStrategy
    from app.ranking.strategies.report_selection import ReportSelectionStrategy, DailyReportStrategy, WeeklyReportStrategy

    context = RankingContextDTO(context_name="test", time_window_hours=24, max_results=50)

    strategies = [
        ("News Ranking", NewsRankingStrategy()),
        ("Board News (AI)", BoardNewsRankingStrategy("ai")),
        ("Tech Ranking", TechRankingStrategy()),
        ("Deep Tech", DeepTechRankingStrategy()),
        ("Engineering", EngineeringRankingStrategy()),
        ("Homepage", HomepageRankingStrategy()),
        ("Diversified Homepage", DiversifiedHomepageStrategy()),
        ("Trend", TrendRankingStrategy()),
        ("Emerging Trend", EmergingTrendStrategy()),
        ("Hot Trend", HotTrendStrategy()),
        ("Report Selection", ReportSelectionStrategy()),
        ("Daily Report", DailyReportStrategy()),
        ("Weekly Report", WeeklyReportStrategy()),
    ]

    for name, strategy in strategies:
        print(f"\n{name} ({strategy.strategy_name})")
        print("-" * 40)
        weights = strategy.get_weights(context)
        for feature, weight in sorted(weights.items(), key=lambda x: -x[1]):
            bar = "█" * int(weight * 20)
            print(f"  {feature:25} {weight:5.0%} {bar}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Debug ranking analysis")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # topic command
    topic_parser = subparsers.add_parser("topic", help="Debug single topic")
    topic_parser.add_argument("topic_id", type=int, help="Topic ID")
    topic_parser.add_argument("--context", default="news_feed", help="Ranking context")

    # compare command
    compare_parser = subparsers.add_parser("compare", help="Compare topics")
    compare_parser.add_argument("topic_ids", help="Comma-separated topic IDs")
    compare_parser.add_argument("--context", default="news_feed", help="Ranking context")

    # features command
    features_parser = subparsers.add_parser("features", help="Show features")
    features_parser.add_argument("topic_id", type=int, help="Topic ID")

    # strategies command
    subparsers.add_parser("strategies", help="Show all strategies")

    args = parser.parse_args()

    if args.command == "topic":
        asyncio.run(debug_topic_ranking(args.topic_id, args.context))
    elif args.command == "compare":
        topic_ids = [int(x.strip()) for x in args.topic_ids.split(",")]
        asyncio.run(compare_topics(topic_ids, args.context))
    elif args.command == "features":
        asyncio.run(show_features(args.topic_id))
    elif args.command == "strategies":
        asyncio.run(show_strategies())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
