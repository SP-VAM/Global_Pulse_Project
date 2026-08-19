"""Phase 1A — Error handling and unknown route tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_unknown_route_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_route_uses_standard_error_format(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nonexistent-endpoint")
    body = response.json()
    assert "error" in body
    error = body["error"]
    assert "code" in error
    assert "message" in error
    assert "timestampUtc" in error


@pytest.mark.asyncio
async def test_unknown_route_error_code_is_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/v1/unknown")
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_root_path_returns_health(client: AsyncClient) -> None:
    """Root path is the registered health check route."""
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_error_response_has_timestamp_utc(client: AsyncClient) -> None:
    response = await client.get("/api/v1/not-a-real-path")
    error = response.json()["error"]
    assert error["timestampUtc"]
    # Basic ISO 8601 check
    assert "T" in error["timestampUtc"]
