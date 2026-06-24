import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient


async def _setup_user_with_due_question(client: AsyncClient, email: str):
    await client.post("/api/v1/auth/register",
        json={"email": email, "password": "password123"})
    login = await client.post("/api/v1/auth/login",
        json={"email": email, "password": "password123"})
    token = login.json()["data"]["access_token"]
    # 创建一道题
    create = await client.post("/api/v1/questions",
        json={"content": "复习题", "correct_answer": "答案"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]
    return token, qid


@pytest.mark.asyncio
async def test_review_queue_returns_due_items(client: AsyncClient):
    token, _ = await _setup_user_with_due_question(client, "rv1@test.com")
    resp = await client.get("/api/v1/review/queue",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_score_updates_sm2_params(client: AsyncClient):
    token, qid = await _setup_user_with_due_question(client, "rv2@test.com")
    resp = await client.post(f"/api/v1/review/{qid}/score",
        json={"score": 4},
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["score"] == 4
    assert data["new_interval_days"] >= 1
    assert data["new_ease_factor"] >= 1.3
    assert data["next_review_at"] is not None


@pytest.mark.asyncio
async def test_score_invalid_range(client: AsyncClient):
    token, qid = await _setup_user_with_due_question(client, "rv3@test.com")
    resp = await client.post(f"/api/v1/review/{qid}/score",
        json={"score": 6},  # 超出范围
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_stats_returns_counts(client: AsyncClient):
    token, _ = await _setup_user_with_due_question(client, "rv4@test.com")
    resp = await client.get("/api/v1/review/stats",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "due_count" in data
    assert "reviewed_today" in data
