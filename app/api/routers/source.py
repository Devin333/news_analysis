"""Source management API router."""

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.source import (
    SourceCreateRequest,
    SourceListResponse,
    SourceResponse,
    SourceUpdateRequest,
)
from app.common.exceptions import ValidationError
from app.contracts.dto.source import SourceCreate, SourceUpdate
from app.source_management.service import SourceService
from app.source_management.validators import SourceValidator

router = APIRouter(prefix="/sources", tags=["sources"])
service = SourceService()


def _to_response(item) -> SourceResponse:  # noqa: ANN001
    return SourceResponse(**item.model_dump())


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(payload: SourceCreateRequest) -> SourceResponse:
    data = SourceCreate(**payload.model_dump())
    try:
        SourceValidator.validate_create(data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    created = await service.create_source(data)
    return _to_response(created)


@router.get("", response_model=SourceListResponse)
async def list_sources(active_only: bool = False) -> SourceListResponse:
    items = await service.list_sources(active_only=active_only)
    responses = [_to_response(item) for item in items]
    return SourceListResponse(items=responses, total=len(responses))


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: int) -> SourceResponse:
    source = await service.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return _to_response(source)


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(source_id: int, payload: SourceUpdateRequest) -> SourceResponse:
    data = SourceUpdate(**payload.model_dump(exclude_unset=True))
    try:
        SourceValidator.validate_update(data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    updated = await service.update_source(source_id, data)
    if updated is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return _to_response(updated)


@router.post("/{source_id}/enable", status_code=status.HTTP_204_NO_CONTENT)
async def enable_source(source_id: int) -> None:
    success = await service.enable_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found")


@router.post("/{source_id}/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_source(source_id: int) -> None:
    success = await service.disable_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found")
