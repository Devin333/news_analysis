"""Integration tests for health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.app import app


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test /health returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_returns_app_info(client):
    """Test /health returns application info."""
    response = await client.get("/health")
    data = response.json()
    assert data["app_name"] == "NewsAgent"
    assert data["environment"] in ["development", "staging", "production", "test"]
