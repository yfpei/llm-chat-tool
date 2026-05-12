import pytest


async def _setup(client):
    """Register a user and return auth headers + user id."""
    resp = await client.post("/api/auth/register", json={"username": "conv_test", "password": "test1234"})
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_create_conversation(client):
    headers = await _setup(client)
    resp = await client.post("/api/conversations", json={"title": "Test Chat"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Chat"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_conversation_default_title(client):
    headers = await _setup(client)
    resp = await client.post("/api/conversations", json={}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "新会话"


@pytest.mark.asyncio
async def test_list_conversations(client):
    headers = await _setup(client)
    await client.post("/api/conversations", json={"title": "Chat 1"}, headers=headers)
    await client.post("/api/conversations", json={"title": "Chat 2"}, headers=headers)
    resp = await client.get("/api/conversations", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_conversation_detail(client):
    headers = await _setup(client)
    create_resp = await client.post("/api/conversations", json={"title": "Detail Test"}, headers=headers)
    conv_id = create_resp.json()["id"]
    resp = await client.get(f"/api/conversations/{conv_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Detail Test"
    assert "messages" in data


@pytest.mark.asyncio
async def test_delete_conversation(client):
    headers = await _setup(client)
    create_resp = await client.post("/api/conversations", json={"title": "To Delete"}, headers=headers)
    conv_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/conversations/{conv_id}", headers=headers)
    assert resp.status_code == 200
    list_resp = await client.get("/api/conversations", headers=headers)
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_update_conversation(client):
    headers = await _setup(client)
    create_resp = await client.post("/api/conversations", json={"title": "Old"}, headers=headers)
    conv_id = create_resp.json()["id"]
    resp = await client.put(f"/api/conversations/{conv_id}", json={"title": "New"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
