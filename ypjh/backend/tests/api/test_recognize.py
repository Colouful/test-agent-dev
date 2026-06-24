import pytest
from httpx import AsyncClient

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 200


@pytest.mark.asyncio
async def test_recognize_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/questions/recognize",
        files={"image": ("test.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_recognize_returns_result(client: AsyncClient) -> None:
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "recog@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "recog@test.com", "password": "password123"},
    )
    token = login.json()["data"]["access_token"]

    resp = await client.post(
        "/api/v1/questions/recognize",
        files={"image": ("test.jpg", JPEG_BYTES, "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["status"] in ("high_confidence", "pending_review", "error")


@pytest.mark.asyncio
async def test_recognize_invalid_file_type(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "recog2@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "recog2@test.com", "password": "password123"},
    )
    token = login.json()["data"]["access_token"]

    resp = await client.post(
        "/api/v1/questions/recognize",
        files={"image": ("hack.jpg", b"#!/bin/bash", "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "error"
    assert resp.json()["data"]["error_code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_recognize_file_too_large(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "recog3@test.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "recog3@test.com", "password": "password123"},
    )
    token = login.json()["data"]["access_token"]

    big_file = b"\xff\xd8\xff" + b"\x00" * (21 * 1024 * 1024)  # 21MB
    resp = await client.post(
        "/api/v1/questions/recognize",
        files={"image": ("big.jpg", big_file, "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 413
