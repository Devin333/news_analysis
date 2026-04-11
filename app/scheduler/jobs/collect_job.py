"""Collect job - wired up with collector manager and raw item ingestion."""

import hashlib
import time
from datetime import datetime, timezone

from app.bootstrap.logging import get_logger
from app.collectors.manager import CollectorManager
from app.collectors.registry import CollectorRegistry, get_registry
from app.contracts.dto.raw_item import RawItemDTO
from app.contracts.dto.source import SourceRead
from app.scheduler.models import JobRunResult
from app.source_management.service import SourceService
from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


def _compute_checksum(content: str | None) -> str:
    """Compute SHA-256 checksum for dedup."""
    if not content:
        return ""
    return hashlib.sha256(content.encode()).hexdigest()


def _raw_collected_to_dto(
    source_id: int,
    item,  # RawCollectedItem
) -> RawItemDTO:
    """Convert a RawCollectedItem from collector output to RawItemDTO for storage."""
    # Build checksum from URL + title + raw content
    parts = [item.url or "", item.title or ""]
    if item.raw_text:
        parts.append(item.raw_text[:500])
    elif item.raw_html:
        parts.append(item.raw_html[:500])
    checksum = _compute_checksum("|".join(parts))

    return RawItemDTO(
        source_id=source_id,
        external_id=item.external_id,
        url=item.url,
        canonical_url=item.canonical_url,
        raw_html=item.raw_html,
        raw_json=item.raw_json,
        raw_text=item.raw_text,
        fetched_at=item.published_at or datetime.now(timezone.utc),
        checksum=checksum,
        parse_status="pending",
    )


async def run_collect_job(
    source_id: int | None = None,
    registry: CollectorRegistry | None = None,
) -> JobRunResult:
    """Execute a collection job for a single source or all active sources.

    Pipeline:
    1. Get source(s) from repository via SourceService.
    2. Find matching collector from registry.
    3. Execute collection via CollectorManager.
    4. Convert collected items to RawItemDTOs.
    5. Store raw items via UnitOfWork (with dedup by checksum).

    Args:
        source_id: Specific source to collect. If None, collects all active sources.
        registry: Optional custom CollectorRegistry. Defaults to global registry.

    Returns:
        JobRunResult with execution details.
    """
    start_time = time.monotonic()
    job_label = f"collect_{source_id or 'all'}"
    logger.info(f"Starting collect job ({job_label})")

    try:
        # Resolve registry
        reg = registry or get_registry()
        manager = CollectorManager(reg)

        # 1. Get source(s)
        source_service = SourceService()
        if source_id:
            source = await source_service.get_source(source_id)
            if source is None:
                return JobRunResult(
                    job_id=job_label,
                    success=False,
                    message=f"Source {source_id} not found",
                    error=f"Source {source_id} not found",
                    duration_seconds=round(time.monotonic() - start_time, 3),
                )
            sources = [source]
        else:
            sources = await source_service.list_sources(active_only=True)

        if not sources:
            return JobRunResult(
                job_id=job_label,
                success=True,
                message="No active sources to collect",
                items_processed=0,
                duration_seconds=round(time.monotonic() - start_time, 3),
            )

        # 2-3. Execute collection via manager
        collect_results = await manager.collect_many(sources)

        # 4-5. Ingest raw items
        total_stored = 0
        total_skipped = 0
        errors: list[str] = []

        for collect_result in collect_results:
            if not collect_result.success:
                errors.append(
                    f"Source {collect_result.source_id}: {collect_result.error}"
                )
                continue

            if not collect_result.items:
                continue

            # Convert to DTOs
            dtos = [
                _raw_collected_to_dto(collect_result.source_id, item)
                for item in collect_result.items
            ]

            # Store with dedup
            async with UnitOfWork() as uow:
                assert uow.raw_items is not None
                for dto in dtos:
                    # Skip if already exists by checksum
                    if dto.checksum and await uow.raw_items.exists_by_checksum(
                        dto.checksum
                    ):
                        total_skipped += 1
                        continue
                    await uow.raw_items.create(dto)
                    total_stored += 1

        duration = time.monotonic() - start_time
        success = len(errors) == 0
        message = (
            f"Collected {total_stored} new items"
            + (f", skipped {total_skipped} duplicates" if total_skipped else "")
            + (f", {len(errors)} errors" if errors else "")
        )

        logger.info(
            f"Collect job {job_label} completed: "
            f"{total_stored} stored, {total_skipped} skipped in {duration:.3f}s"
        )

        return JobRunResult(
            job_id=job_label,
            success=success,
            message=message,
            items_processed=total_stored,
            duration_seconds=round(duration, 3),
            metadata={
                "sources_processed": len(sources),
                "items_skipped_dedup": total_skipped,
                "errors": errors,
            },
        )

    except Exception as exc:  # noqa: BLE001
        duration = time.monotonic() - start_time
        logger.error(f"Collect job failed: {exc}")
        return JobRunResult(
            job_id=job_label,
            success=False,
            message="Collect job failed",
            error=str(exc),
            duration_seconds=round(duration, 3),
        )
