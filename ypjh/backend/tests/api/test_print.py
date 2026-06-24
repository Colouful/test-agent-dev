import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register",
        json={"email": email, "password": "password123"})
    resp = await client.post("/api/v1/auth/login",
        json={"email": email, "password": "password123"})
    return resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_print_preview_returns_html(client: AsyncClient):
    token = await _get_token(client, "print1@test.com")
    create = await client.post("/api/v1/questions",
        json={"content": "1+1=?", "correct_answer": "2"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]

    resp = await client.post(
        "/api/v1/print/preview",
        json={"question_ids": [qid], "show_answer": True, "layout": "single"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "1+1=?" in resp.text
    assert "KaTeX" in resp.text or "katex" in resp.text


@pytest.mark.asyncio
async def test_print_preview_hides_answer(client: AsyncClient):
    token = await _get_token(client, "print2@test.com")
    create = await client.post("/api/v1/questions",
        json={"content": "题目内容", "correct_answer": "秘密答案"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]

    resp = await client.post(
        "/api/v1/print/preview",
        json={"question_ids": [qid], "show_answer": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "秘密答案" not in resp.text


@pytest.mark.asyncio
async def test_print_user_isolation(client: AsyncClient):
    token1 = await _get_token(client, "print3@test.com")
    token2 = await _get_token(client, "print4@test.com")
    create = await client.post("/api/v1/questions",
        json={"content": "私密题目", "correct_answer": "A"},
        headers={"Authorization": f"Bearer {token1}"})
    qid = create.json()["data"]["id"]

    # user2 用 user1 的题目 id → 应返回空（或跳过该 id）
    resp = await client.post(
        "/api/v1/print/preview",
        json={"question_ids": [qid]},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 200
    assert "私密题目" not in resp.text  # R1: 跨用户题目不出现


@pytest.mark.asyncio
async def test_print_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/print/preview",
        json={"question_ids": ["any-id"]})
    assert resp.status_code == 401
