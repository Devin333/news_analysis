"""Process job for scheduled processing of raw items."""

import time

from app.bootstrap.logging import get_logger
from app.common.enums import ContentType
from app.contracts.dto.raw_item import RawItemDTO
from app.processing.pipeline import ProcessingPipeline
from app.scheduler.models import JobRunResult
from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


async def run_process_job(
    source_id: int | None = None,
    limit: int = 100,
) -> JobRunResult:
    """Process pending raw items through the pipeline.

    Pipeline:
    1. Fetch raw items with parse_status='pending'
    2. Run through processing pipeline
    3. Store normalized items
    4. Update raw item parse_status

    Args:
        source_id: Optional source ID to filter items.
        limit: Maximum items to process per run.

    Returns:
        JobRunResult with execution details.
    """
    start_time = time.monotonic()
    job_label = f"process_{source_id or 'all'}"
    logger.info(f"Starting process job ({job_label})")

    try:
        # 1. Fetch pending raw items
        async with UnitOfWork() as uow:
            assert uow.raw_items is not None

            if source_id:
                raw_items = await uow.raw_items.list_by_source(source_id, limit=limit)
            else:
                # For now, just process from all sources
                # In production, would have a method to get pending items
                raw_items = []

        if not raw_items:
            return JobRunResult(
                job_id=job_label,
                success=True,
                message="No pending items to process",
                items_processed=0,
                duration_seconds=round(time.monotonic() - start_time, 3),
            )

        # 2. Run through pipeline
        pipeline = ProcessingPipeline()

        # Fetch existing normalized items for dedup
        async with UnitOfWork() as uow:
            assert uow.normalized_items is not None
            existing = await uow.normalized_items.list_recent(limit=1000)

        # Convert to list of RawItemDTO
        raw_item_dtos = [
            RawItemDTO(
                id=item.id,
                source_id=item.source_id,
                external_id=item.external_id,
                url=item.url,
                canonical_url=item.canonical_url,
                raw_html=item.raw_html,
                raw_json=item.raw_json,
                raw_text=item.raw_text,
                fetched_at=item.fetched_at,
                checksum=item.checksum,
                parse_status=item.parse_status,
            )
            for item in raw_items
        ]

        result = pipeline.process(
            raw_item_dtos,
            content_type=ContentType.ARTICLE,
            existing_items=existing,
        )

        # 3. Store normalized items
        stored_count = 0
        async with UnitOfWork() as uow:
            assert uow.normalized_items is not None
            for normalized in result.items:
                await uow.normalized_items.create(normalized)
                stored_count += 1

        duration = time.monotonic() - start_time
        message = (
            f"Processed {result.total_input} items: "
            f"{stored_count} stored, {len(result.duplicates)} duplicates, "
            f"{result.failed_count} failed"
        )

        logger.info(f"Process job {job_label} completed in {duration:.3f}s")

        return JobRunResult(
            job_id=job_label,
            success=True,
            message=message,
            items_processed=stored_count,
            duration_seconds=round(duration, 3),
            metadata={
                "total_input": result.total_input,
                "parsed": result.parsed_count,
                "normalized": result.normalized_count,
                "duplicates": len(result.duplicates),
                "failed": result.failed_count,
            },
        )

    except Exception as exc:  # noqa: BLE001
        duration = time.monotonic() - start_time
        logger.error(f"Process job failed: {exc}")
        return JobRunResult(
            job_id=job_label,
            success=False,
            message="Process job failed",
            error=str(exc),
            duration_seconds=round(duration, 3),
        )
