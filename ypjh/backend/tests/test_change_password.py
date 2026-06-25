import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.fixture
async def auth_headers(client: AsyncClient):
    # 注册并登录，获取 token
    await client.post("/api/v1/auth/register",
                      json={"email": "pw@test.com", "password": "oldpass123"})
    resp = await client.post("/api/v1/auth/login",
                             json={"email": "pw@test.com", "password": "oldpass123"})
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_change_password_success(client, auth_headers):
    resp = await client.patch(
        "/api/v1/auth/password",
        json={"old_password": "oldpass123", "new_password": "newpass456"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["message"] == "密码已更新"


@pytest.mark.asyncio
async def test_change_password_wrong_old(client, auth_headers):
    resp = await client.patch(
        "/api/v1/auth/password",
        json={"old_password": "wrongpass", "new_password": "newpass456"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "WRONG_PASSWORD"


@pytest.mark.asyncio
async def test_change_password_too_short(client, auth_headers):
    resp = await client.patch(
        "/api/v1/auth/password",
        json={"old_password": "oldpass123", "new_password": "short"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
