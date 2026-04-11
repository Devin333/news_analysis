"""Unit tests for source repository."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.enums import SourceType
from app.contracts.dto.source import SourceCreate, SourceUpdate
from app.source_management.models import Source
from app.source_management.repository import SourceRepository


@pytest.mark.asyncio
async def test_create_source() -> None:
    """Repository create should return SourceRead DTO."""
    session = AsyncMock()
    session.add = MagicMock()
    repo = SourceRepository(session)

    async def _flush_side_effect() -> None:
        added = session.add.call_args.args[0]
        added.id = 1
        added.trust_score = Decimal("0.80")

    session.flush.side_effect = _flush_side_effect

    data = SourceCreate(
        name="Hacker News",
        source_type=SourceType.RSS,
        feed_url="https://news.ycombinator.com/rss",
    )

    result = await repo.create(data)

    assert result.id == 1
    assert result.name == "Hacker News"
    assert result.source_type == SourceType.RSS
    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found() -> None:
    """Repository should return None when source does not exist."""
    session = AsyncMock()
    repo = SourceRepository(session)

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    session.execute.return_value = execute_result

    result = await repo.get_by_id(999)

    assert result is None


@pytest.mark.asyncio
async def test_update_source() -> None:
    """Repository update should mutate and return updated source."""
    session = AsyncMock()
    repo = SourceRepository(session)

    source = Source(
        name="Old Name",
        source_type=SourceType.RSS,
        priority=100,
        trust_score=Decimal("0.5"),
        fetch_interval_minutes=60,
        is_active=True,
        metadata_json={},
    )
    source.id = 10

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = source
    session.execute.return_value = execute_result

    data = SourceUpdate(name="New Name", priority=10)
    result = await repo.update(10, data)

    assert result is not None
    assert result.name == "New Name"
    assert result.priority == 10
    session.flush.assert_called_once()
