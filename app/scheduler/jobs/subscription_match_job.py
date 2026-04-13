"""Subscription match job for scheduled matching."""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.storage.repositories.report_repository import ReportRepository
    from app.storage.repositories.topic_repository import TopicRepository
    from app.subscription.service import SubscriptionService

logger = get_logger(__name__)


class SubscriptionMatchJob:
    """Job for matching new content against subscriptions.

    Runs periodically to:
    - Scan new topics
    - Scan new reports
    - Scan new trends
    - Record matches
    """

    def __init__(
        self,
        subscription_service: "SubscriptionService | None" = None,
        topic_repo: "TopicRepository | None" = None,
        report_repo: "ReportRepository | None" = None,
    ) -> None:
        """Initialize the job.

        Args:
            subscription_service: Subscription service.
            topic_repo: Topic repository.
            report_repo: Report repository.
        """
        self._subscription_service = subscription_service
        self._topic_repo = topic_repo
        self._report_repo = report_repo
        self._last_run_at: datetime | None = None

    async def run(
        self,
        *,
        lookback_hours: int = 1,
        scan_topics: bool = True,
        scan_reports: bool = True,
        scan_trends: bool = True,
    ) -> dict[str, Any]:
        """Run the subscription match job.

        Args:
            lookback_hours: Hours to look back for new content.
            scan_topics: Whether to scan topics.
            scan_reports: Whether to scan reports.
            scan_trends: Whether to scan trends.

        Returns:
            Job result summary.
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting subscription match job, lookback={lookback_hours}h")

        results: dict[str, Any] = {
            "started_at": start_time.isoformat(),
            "topics_scanned": 0,
            "reports_scanned": 0,
            "trends_scanned": 0,
            "topic_matches": 0,
            "report_matches": 0,
            "trend_matches": 0,
            "total_matches": 0,
            "subscriptions_matched": set(),
            "errors": [],
        }

        if not self._subscription_service:
            results["errors"].append("Subscription service not configured")
            results["subscriptions_matched"] = []
            return results

        cutoff = start_time - timedelta(hours=lookback_hours)

        # Scan topics
        if scan_topics and self._topic_repo:
            topic_results = await self._scan_topics(cutoff)
            results["topics_scanned"] = topic_results["scanned"]
            results["topic_matches"] = topic_results["matches"]
            results["subscriptions_matched"].update(topic_results["subscriptions"])
            results["errors"].extend(topic_results["errors"])

        # Scan reports
        if scan_reports and self._report_repo:
            report_results = await self._scan_reports(cutoff)
            results["reports_scanned"] = report_results["scanned"]
            results["report_matches"] = report_results["matches"]
            results["subscriptions_matched"].update(report_results["subscriptions"])
            results["errors"].extend(report_results["errors"])

        # Scan trends (using topic trend signals)
        if scan_trends and self._topic_repo:
            trend_results = await self._scan_trends(cutoff)
            results["trends_scanned"] = trend_results["scanned"]
            results["trend_matches"] = trend_results["matches"]
            results["subscriptions_matched"].update(trend_results["subscriptions"])
            results["errors"].extend(trend_results["errors"])

        # Calculate totals
        results["total_matches"] = (
            results["topic_matches"]
            + results["report_matches"]
            + results["trend_matches"]
        )
        results["subscriptions_matched"] = list(results["subscriptions_matched"])

        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        results["duration_seconds"] = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds()

        self._last_run_at = start_time

        logger.info(
            f"Subscription match job completed: "
            f"topics={results['topics_scanned']}, "
            f"reports={results['reports_scanned']}, "
            f"trends={results['trends_scanned']}, "
            f"total_matches={results['total_matches']}"
        )

        return results

    async def _scan_topics(self, cutoff: datetime) -> dict[str, Any]:
        """Scan recent topics for matches.

        Args:
            cutoff: Cutoff datetime.

        Returns:
            Scan results.
        """
        results: dict[str, Any] = {
            "scanned": 0,
            "matches": 0,
            "subscriptions": set(),
            "errors": [],
        }

        if not self._topic_repo or not self._subscription_service:
            return results

        try:
            topics = await self._get_recent_topics(cutoff)
            results["scanned"] = len(topics)

            for topic in topics:
                try:
                    match_result = await self._subscription_service.match_topic_against_subscriptions(
                        topic_id=topic.id,
                        topic_title=topic.title,
                        topic_summary=topic.summary,
                        topic_tags=self._get_topic_tags(topic),
                        board_type=str(topic.board_type) if topic.board_type else None,
                    )

                    if match_result.total_matches > 0:
                        results["matches"] += match_result.total_matches
                        results["subscriptions"].update(match_result.matched_subscriptions)

                except Exception as e:
                    logger.error(f"Error matching topic {topic.id}: {e}")
                    results["errors"].append(f"Topic {topic.id}: {str(e)}")

        except Exception as e:
            logger.error(f"Error scanning topics: {e}")
            results["errors"].append(f"Topic scan: {str(e)}")

        return results

    async def _scan_reports(self, cutoff: datetime) -> dict[str, Any]:
        """Scan recent reports for matches.

        Args:
            cutoff: Cutoff datetime.

        Returns:
            Scan results.
        """
        results: dict[str, Any] = {
            "scanned": 0,
            "matches": 0,
            "subscriptions": set(),
            "errors": [],
        }

        if not self._report_repo or not self._subscription_service:
            return results

        try:
            reports = await self._get_recent_reports(cutoff)
            results["scanned"] = len(reports)

            for report in reports:
                try:
                    # Match report as a special content type
                    match_result = await self._subscription_service.match_topic_against_subscriptions(
                        topic_id=report.id,
                        topic_title=report.title or f"Report {report.report_type}",
                        topic_summary=report.summary,
                        topic_tags=[],  # Reports don't have tags directly
                        board_type=None,
                    )

                    if match_result.total_matches > 0:
                        results["matches"] += match_result.total_matches
                        results["subscriptions"].update(match_result.matched_subscriptions)

                except Exception as e:
                    logger.error(f"Error matching report {report.id}: {e}")
                    results["errors"].append(f"Report {report.id}: {str(e)}")

        except Exception as e:
            logger.error(f"Error scanning reports: {e}")
            results["errors"].append(f"Report scan: {str(e)}")

        return results

    async def _scan_trends(self, cutoff: datetime) -> dict[str, Any]:
        """Scan recent trends for matches.

        Args:
            cutoff: Cutoff datetime.

        Returns:
            Scan results.
        """
        results: dict[str, Any] = {
            "scanned": 0,
            "matches": 0,
            "subscriptions": set(),
            "errors": [],
        }

        if not self._topic_repo or not self._subscription_service:
            return results

        try:
            # Get topics with trend signals
            trending_topics = await self._get_trending_topics(cutoff)
            results["scanned"] = len(trending_topics)

            for topic in trending_topics:
                try:
                    # Match trending topic with trend context
                    match_result = await self._subscription_service.match_topic_against_subscriptions(
                        topic_id=topic.id,
                        topic_title=f"[Trending] {topic.title}",
                        topic_summary=topic.summary,
                        topic_tags=self._get_topic_tags(topic) + ["trending"],
                        board_type=str(topic.board_type) if topic.board_type else None,
                    )

                    if match_result.total_matches > 0:
                        results["matches"] += match_result.total_matches
                        results["subscriptions"].update(match_result.matched_subscriptions)

                except Exception as e:
                    logger.error(f"Error matching trend {topic.id}: {e}")
                    results["errors"].append(f"Trend {topic.id}: {str(e)}")

        except Exception as e:
            logger.error(f"Error scanning trends: {e}")
            results["errors"].append(f"Trend scan: {str(e)}")

        return results

    async def _get_recent_topics(self, cutoff: datetime) -> list[Any]:
        """Get topics created/updated after cutoff.

        Args:
            cutoff: Cutoff datetime.

        Returns:
            List of recent topics.
        """
        if not self._topic_repo:
            return []

        topics = await self._topic_repo.list_recent(limit=200)

        return [
            t for t in topics
            if t.last_seen_at and t.last_seen_at >= cutoff
        ]

    async def _get_recent_reports(self, cutoff: datetime) -> list[Any]:
        """Get reports created after cutoff.

        Args:
            cutoff: Cutoff datetime.

        Returns:
            List of recent reports.
        """
        if not self._report_repo:
            return []

        try:
            reports = await self._report_repo.list_recent(limit=50)
            return [
                r for r in reports
                if r.created_at and r.created_at >= cutoff
            ]
        except Exception:
            # Repository may not have list_recent method
            return []

    async def _get_trending_topics(self, cutoff: datetime) -> list[Any]:
        """Get trending topics.

        Args:
            cutoff: Cutoff datetime.

        Returns:
            List of trending topics.
        """
        if not self._topic_repo:
            return []

        try:
            # Get topics with high trend scores
            topics = await self._topic_repo.list_recent(limit=100)
            # Filter for topics that might be trending
            # This is a simplified check - real implementation would use trend_signal table
            return [
                t for t in topics
                if t.last_seen_at and t.last_seen_at >= cutoff
                and getattr(t, "item_count", 0) >= 3  # Multiple sources
            ]
        except Exception:
            return []

    def _get_topic_tags(self, topic: Any) -> list[str]:
        """Get tags for a topic.

        Args:
            topic: Topic model.

        Returns:
            List of tags.
        """
        # Try to get tags from topic_tags relationship
        if hasattr(topic, "tags") and topic.tags:
            return [t.name for t in topic.tags if hasattr(t, "name")]
        return []

    def get_last_run_at(self) -> datetime | None:
        """Get last run timestamp.

        Returns:
            Last run datetime or None.
        """
        return self._last_run_at


async def run_subscription_match_job(
    subscription_service: "SubscriptionService",
    topic_repo: "TopicRepository",
    report_repo: "ReportRepository | None" = None,
    *,
    lookback_hours: int = 1,
    scan_topics: bool = True,
    scan_reports: bool = True,
    scan_trends: bool = True,
) -> dict[str, Any]:
    """Convenience function to run subscription match job.

    Args:
        subscription_service: Subscription service.
        topic_repo: Topic repository.
        report_repo: Report repository.
        lookback_hours: Hours to look back.
        scan_topics: Whether to scan topics.
        scan_reports: Whether to scan reports.
        scan_trends: Whether to scan trends.

    Returns:
        Job result.
    """
    job = SubscriptionMatchJob(
        subscription_service=subscription_service,
        topic_repo=topic_repo,
        report_repo=report_repo,
    )
    return await job.run(
        lookback_hours=lookback_hours,
        scan_topics=scan_topics,
        scan_reports=scan_reports,
        scan_trends=scan_trends,
    )
