"""Source service using Unit of Work."""

from app.contracts.dto.source import SourceCreate, SourceRead, SourceUpdate
from app.storage.uow import UnitOfWork


class SourceService:
    """Business service for source management."""

    async def create_source(self, data: SourceCreate) -> SourceRead:
        async with UnitOfWork() as uow:
            assert uow.sources is not None
            return await uow.sources.create(data)

    async def get_source(self, source_id: int) -> SourceRead | None:
        async with UnitOfWork() as uow:
            assert uow.sources is not None
            return await uow.sources.get_by_id(source_id)

    async def list_sources(self, *, active_only: bool = False) -> list[SourceRead]:
        async with UnitOfWork() as uow:
            assert uow.sources is not None
            return await uow.sources.list_all(active_only=active_only)

    async def update_source(
        self, source_id: int, data: SourceUpdate
    ) -> SourceRead | None:
        async with UnitOfWork() as uow:
            assert uow.sources is not None
            return await uow.sources.update(source_id, data)

    async def enable_source(self, source_id: int) -> bool:
        async with UnitOfWork() as uow:
            assert uow.sources is not None
            return await uow.sources.enable(source_id)

    async def disable_source(self, source_id: int) -> bool:
        async with UnitOfWork() as uow:
            assert uow.sources is not None
            return await uow.sources.disable(source_id)
