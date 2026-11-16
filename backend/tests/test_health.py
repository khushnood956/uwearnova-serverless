"""
Tests for Health, Readiness, and Core Scaffold Behavior
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_liveness(async_client: AsyncClient):
    """Test /health root liveness endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_health_readiness_structure(async_client: AsyncClient):
    """Test /ready root readiness endpoint response structure and services status."""
    response = await async_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ready", "degraded")
    assert "services" in data
    assert data["services"]["api"] == "healthy"
    assert data["services"]["database"] in ("healthy", "unhealthy")


@pytest.mark.asyncio
async def test_readiness_with_healthy_database(async_client: AsyncClient, monkeypatch):
    """Test /ready reports 'ready' when database ping succeeds."""
    async def mock_db_healthy(*args, **kwargs):
        return True

    monkeypatch.setattr("app.api.v1.endpoints.health.check_database_health", mock_db_healthy)
    response = await async_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["services"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_with_unhealthy_database(async_client: AsyncClient, monkeypatch):
    """Test /ready reports 'degraded' when database ping fails."""
    async def mock_db_unhealthy(*args, **kwargs):
        return False

    monkeypatch.setattr("app.api.v1.endpoints.health.check_database_health", mock_db_unhealthy)
    response = await async_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["database"] == "unhealthy"


@pytest.mark.asyncio
async def test_versioned_health_liveness(async_client: AsyncClient):
    """Test /api/v1/health versioned liveness endpoint."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_openapi_schema_available(async_client: AsyncClient):
    """Test that OpenAPI schema is properly served under /api/v1/openapi.json."""
    response = await async_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "UniNova API"


@pytest.mark.asyncio
async def test_standard_404_error_envelope(async_client: AsyncClient):
    """Test that 404 responses conform to the standard error envelope."""
    response = await async_client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]
