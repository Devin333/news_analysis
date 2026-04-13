"""Agent workflow jobs for daily execution.

This module defines scheduled jobs that orchestrate agent execution.
"""

from datetime import datetime, timezone

from app.bootstrap.logging import get_logger
from app.scheduler.models import JobRunResult

logger = get_logger(__name__)


async def process_raw_items_job() -> JobRunResult:
    """Job: Process pending raw items into normalized items and topics.

    Pipeline:
    1. Fetch raw items with parse_status='pending'
    2. Parse and normalize them
    3. Enrich with classification and tags
    4. Resolve into topics (create new or merge into existing)
    5. Store normalized items and update topics
    """
    job_id = "process_raw_items"
    start_time = datetime.now(timezone.utc)

    try:
        from app.common.enums import ContentType
        from app.processing.pipeline import ProcessingPipeline
        from app.processing.enrichment_pipeline import get_enrichment_pipeline
        from app.editorial.topic_service import TopicService
        from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
        from app.storage.repositories.topic_repository import TopicRepository
        from app.storage.uow import UnitOfWork

        pipeline = ProcessingPipeline()
        enrichment = get_enrichment_pipeline()

        total_processed = 0
        total_topics_created = 0
        total_topics_merged = 0
        errors: list[str] = []

        async with UnitOfWork() as uow:
            assert uow.raw_items is not None
            assert uow.normalized_items is not None
            assert uow.topics is not None

            # 1. Fetch pending raw items
            pending_items = await uow.raw_items.list_pending(limit=200)

            if not pending_items:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                return JobRunResult(
                    job_id=job_id,
                    success=True,
                    message="No pending raw items to process",
                    items_processed=0,
                    duration_seconds=duration,
                )

            logger.info(f"Processing {len(pending_items)} pending raw items")

            # 2. Parse and normalize
            pipeline_result = pipeline.process(
                pending_items,
                content_type=ContentType.ARTICLE,
                skip_dedup=False,
            )

            if not pipeline_result.items:
                # Mark raw items as processed even if nothing came out
                for raw_item in pending_items:
                    if raw_item.id:
                        await uow.raw_items.update_parse_status(raw_item.id, "processed")

                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                return JobRunResult(
                    job_id=job_id,
                    success=True,
                    message=f"Parsed {pipeline_result.parsed_count} items, "
                            f"{pipeline_result.failed_count} failed, "
                            f"0 unique after dedup",
                    items_processed=0,
                    duration_seconds=duration,
                )

            # 3. Enrich with classification and tags
            enrichment_results = enrichment.enrich_batch(pipeline_result.items)

            # 4. Store normalized items and resolve into topics
            session = uow.session
            assert session is not None
            topic_service = TopicService(
                TopicRepository(session),
                NormalizedItemRepository(session),
            )

            for item in pipeline_result.items:
                try:
                    # Ensure title is not empty - use URL or excerpt as fallback
                    if not item.title or not item.title.strip():
                        if item.canonical_url:
                            # Extract meaningful title from URL
                            from urllib.parse import urlparse
                            parsed = urlparse(item.canonical_url)
                            path = parsed.path.strip("/").split("/")[-1] if parsed.path else ""
                            item.title = path.replace("-", " ").replace("_", " ").title() or parsed.netloc
                        elif item.excerpt:
                            item.title = item.excerpt[:100]
                        else:
                            item.title = f"Untitled item from source {item.source_id}"

                    # Store normalized item
                    stored_item = await uow.normalized_items.create(item)
                    item.id = stored_item.id

                    # Resolve into topic (create new or merge)
                    topic = await topic_service.resolve_topic_for_item(item)

                    if topic:
                        total_processed += 1
                        # Check if this was a new topic or merge
                        if topic.item_count <= 1:
                            total_topics_created += 1
                        else:
                            total_topics_merged += 1

                except Exception as e:
                    errors.append(f"Failed to process item '{item.title[:50]}': {e}")
                    logger.warning(f"Failed to process item: {e}")
                    continue

            # 5. Mark raw items as processed
            for raw_item in pending_items:
                if raw_item.id:
                    await uow.raw_items.update_parse_status(raw_item.id, "processed")

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        message = (
            f"Processed {total_processed} items into topics "
            f"({total_topics_created} new, {total_topics_merged} merged)"
        )
        if errors:
            message += f", {len(errors)} errors"

        logger.info(f"Process raw items job completed: {message}")

        return JobRunResult(
            job_id=job_id,
            success=len(errors) == 0,
            message=message,
            items_processed=total_processed,
            duration_seconds=duration,
            metadata={
                "topics_created": total_topics_created,
                "topics_merged": total_topics_merged,
                "pipeline_parsed": pipeline_result.parsed_count,
                "pipeline_normalized": pipeline_result.normalized_count,
                "pipeline_deduped": pipeline_result.deduplicated_count,
                "pipeline_failed": pipeline_result.failed_count,
                "errors": errors[:10],  # Limit error list
            },
        )

    except Exception as exc:
        logger.error(f"Process raw items job failed: {exc}")
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        return JobRunResult(
            job_id=job_id,
            success=False,
            error=str(exc),
            duration_seconds=duration,
        )


async def trend_hunter_job() -> JobRunResult:
    """Job: Run TrendHunter agent to identify emerging trends.

    Scans recent topics and identifies emerging trends
    based on activity patterns and signals.
    """
    job_id = "trend_hunter"
    start_time = datetime.now(timezone.utc)

    try:
        from app.agents.trend_hunter.service import TrendHunterService
        from app.storage.uow import UnitOfWork

        async with UnitOfWork() as uow:
            service = TrendHunterService(uow=uow)
            trends = await service.scan_recent_topics(
                window_days=7,
                min_items=3,
                limit=50,
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(f"TrendHunter job completed: {len(trends)} emerging trends found")

            return JobRunResult(
                job_id=job_id,
                success=True,
                message=f"Found {len(trends)} emerging trends",
                items_processed=len(trends),
                duration_seconds=duration,
                metadata={
                    "trend_topic_ids": [t[0] for t in trends],
                },
            )

    except Exception as exc:
        logger.error(f"TrendHunter job failed: {exc}")
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        return JobRunResult(
            job_id=job_id,
            success=False,
            error=str(exc),
            duration_seconds=duration,
        )


async def generate_daily_report_job() -> JobRunResult:
    """Job: Generate daily report.

    Creates a daily summary report of topics and trends.
    """
    job_id = "generate_daily_report"
    start_time = datetime.now(timezone.utc)

    try:
        from app.editorial.report_service import ReportService

        report_date = datetime.now(timezone.utc)

        service = ReportService()
        report = await service.build_daily_report(report_date)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        if report:
            logger.info(f"Daily report generated: {report.title}")
            return JobRunResult(
                job_id=job_id,
                success=True,
                message=f"Generated report: {report.title}",
                items_processed=report.topic_count,
                duration_seconds=duration,
                metadata={
                    "report_id": getattr(report, "id", None),
                    "topic_count": report.topic_count,
                },
            )
        else:
            return JobRunResult(
                job_id=job_id,
                success=True,
                message="No content for daily report",
                items_processed=0,
                duration_seconds=duration,
            )

    except Exception as exc:
        logger.error(f"Daily report job failed: {exc}")
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        return JobRunResult(
            job_id=job_id,
            success=False,
            error=str(exc),
            duration_seconds=duration,
        )


async def writer_enrichment_job() -> JobRunResult:
    """Job: Run Writer agent to generate content for topics.

    Generates feed cards for recent topics that may need
    content enrichment.
    """
    job_id = "writer_enrichment"
    start_time = datetime.now(timezone.utc)

    try:
        from app.agents.writer.service import WriterService
        from app.storage.uow import UnitOfWork

        async with UnitOfWork() as uow:
            service = WriterService(uow=uow)

            # Get recent topics for enrichment
            if uow.topics:
                topics = await uow.topics.list_recent(limit=20)
            else:
                topics = []

            enriched_count = 0
            for topic in topics:
                try:
                    # Generate feed card
                    feed_card, meta = await service.write_feed_card(topic.id)
                    if feed_card:
                        enriched_count += 1
                        logger.debug(f"Enriched topic {topic.id}: {topic.title}")
                except Exception as e:
                    logger.warning(f"Failed to enrich topic {topic.id}: {e}")
                    continue

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(f"Writer enrichment job completed: {enriched_count} topics enriched")

            return JobRunResult(
                job_id=job_id,
                success=True,
                message=f"Enriched {enriched_count} topics",
                items_processed=enriched_count,
                duration_seconds=duration,
            )

    except Exception as exc:
        logger.error(f"Writer enrichment job failed: {exc}")
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        return JobRunResult(
            job_id=job_id,
            success=False,
            error=str(exc),
            duration_seconds=duration,
        )


async def run_daily_workflow() -> JobRunResult:
    """Job: Run the complete daily workflow.

    This is the main orchestration job that runs all daily tasks
    in the correct order:
    1. Collect from all sources
    2. Process raw items into normalized items and topics
    3. Run TrendHunter to identify trends
    4. Run Writer to enrich topics
    5. Generate daily report
    """
    from app.scheduler.jobs.collect_job import run_collect_job

    job_id = "daily_workflow"
    start_time = datetime.now(timezone.utc)

    logger.info("Starting daily workflow...")

    results: list[JobRunResult] = []

    # Step 1: Collect
    logger.info("Step 1/5: Collecting from sources...")
    collect_result = await run_collect_job()
    results.append(collect_result)

    if not collect_result.success:
        logger.warning("Collection had failures, continuing with workflow...")

    # Step 2: Process raw items into normalized items and topics
    logger.info("Step 2/5: Processing raw items into topics...")
    process_result = await process_raw_items_job()
    results.append(process_result)

    if not process_result.success:
        logger.warning("Processing had failures, continuing with workflow...")

    # Step 3: TrendHunter
    logger.info("Step 3/5: Running TrendHunter...")
    trend_result = await trend_hunter_job()
    results.append(trend_result)

    # Step 4: Writer enrichment
    logger.info("Step 4/5: Running Writer enrichment...")
    writer_result = await writer_enrichment_job()
    results.append(writer_result)

    # Step 5: Generate report
    logger.info("Step 5/5: Generating daily report...")
    report_result = await generate_daily_report_job()
    results.append(report_result)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Summarize
    success_count = sum(1 for r in results if r.success)
    total_items = sum(r.items_processed for r in results)

    logger.info(
        f"Daily workflow completed: {success_count}/{len(results)} jobs succeeded, "
        f"{total_items} total items processed in {duration:.1f}s"
    )

    return JobRunResult(
        job_id=job_id,
        success=success_count == len(results),
        message=f"Completed {success_count}/{len(results)} jobs",
        items_processed=total_items,
        duration_seconds=duration,
        metadata={
            "step_results": [
                {"job_id": r.job_id, "success": r.success, "items": r.items_processed}
                for r in results
            ],
        },
    )
