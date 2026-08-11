"""Phase 1A — Health endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_body(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    body = response.json()
    assert body["status"] == "healthy"
    assert "service" in body
    assert "version" in body


@pytest.mark.asyncio
async def test_health_service_name_contains_globalpulse(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    body = response.json()
    assert "GlobalPulse" in body["service"]


@pytest.mark.asyncio
async def test_health_version_format(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    version = response.json()["version"]
    parts = version.split(".")
    assert len(parts) == 3, f"Version '{version}' should be semver (x.y.z)"
