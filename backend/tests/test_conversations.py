import pytest


@pytest.mark.asyncio
async def test_create_conversation(client):
    resp = await client.post("/api/conversations", json={"title": "Test Chat"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Chat"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_conversation_default_title(client):
    resp = await client.post("/api/conversations", json={})
    assert resp.status_code == 200
    assert resp.json()["title"] == "新会话"


@pytest.mark.asyncio
async def test_list_conversations(client):
    await client.post("/api/conversations", json={"title": "Chat 1"})
    await client.post("/api/conversations", json={"title": "Chat 2"})
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_conversation_detail(client):
    create_resp = await client.post("/api/conversations", json={"title": "Detail Test"})
    conv_id = create_resp.json()["id"]
    resp = await client.get(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Detail Test"
    assert "messages" in data


@pytest.mark.asyncio
async def test_delete_conversation(client):
    create_resp = await client.post("/api/conversations", json={"title": "To Delete"})
    conv_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    list_resp = await client.get("/api/conversations")
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_update_conversation(client):
    create_resp = await client.post("/api/conversations", json={"title": "Old"})
    conv_id = create_resp.json()["id"]
    resp = await client.put(f"/api/conversations/{conv_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
