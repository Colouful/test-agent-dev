import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_404_has_unified_error_format(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    # /me without token returns 401 (not 404) — confirm it's still enveloped
    assert resp.status_code in (401, 403, 404)
    body = resp.json()
    assert body["data"] is None
    assert "error" in body
    assert isinstance(body["error"], dict)


@pytest.mark.asyncio
async def test_http_exception_returns_unified_format(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "noexist@example.com", "password": "pass"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["data"] is None
    assert "code" in body["error"]
    assert "message" in body["error"]


@pytest.mark.asyncio
async def test_validation_error_returns_unified_format(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "x"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in body["error"]
