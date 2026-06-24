import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register",
        json={"email": email, "password": "password123"})
    resp = await client.post("/api/v1/auth/login",
        json={"email": email, "password": "password123"})
    return resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_question(client: AsyncClient):
    token = await _get_token(client, "q1@test.com")
    resp = await client.post(
        "/api/v1/questions",
        json={"content": "1+1=?", "correct_answer": "2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["id"] is not None
    assert data["content"] == "1+1=?"


@pytest.mark.asyncio
async def test_list_questions_user_isolation(client: AsyncClient):
    token1 = await _get_token(client, "q2@test.com")
    token2 = await _get_token(client, "q3@test.com")
    await client.post("/api/v1/questions",
        json={"content": "user1题目", "correct_answer": "A"},
        headers={"Authorization": f"Bearer {token1}"})
    resp = await client.get("/api/v1/questions",
        headers={"Authorization": f"Bearer {token2}"})
    assert resp.json()["data"]["total"] == 0  # R1: 隔离


@pytest.mark.asyncio
async def test_delete_soft_delete(client: AsyncClient):
    token = await _get_token(client, "q4@test.com")
    create = await client.post("/api/v1/questions",
        json={"content": "题目", "correct_answer": "答案"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]

    del_resp = await client.delete(f"/api/v1/questions/{qid}",
        headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 204

    # 软删除后查询返回 404
    get_resp = await client.get(f"/api/v1/questions/{qid}",
        headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_update_question(client: AsyncClient):
    token = await _get_token(client, "q5@test.com")
    create = await client.post("/api/v1/questions",
        json={"content": "原内容", "correct_answer": "答案"},
        headers={"Authorization": f"Bearer {token}"})
    qid = create.json()["data"]["id"]

    patch = await client.patch(f"/api/v1/questions/{qid}",
        json={"content": "新内容"},
        headers={"Authorization": f"Bearer {token}"})
    assert patch.status_code == 200
    assert patch.json()["data"]["content"] == "新内容"
