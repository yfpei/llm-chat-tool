import pytest


@pytest.mark.asyncio
async def test_create_key(client):
    resp = await client.post("/api/keys", json={
        "name": "Test OpenAI",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-invalid-key",
        "model": "gpt-4o",
        "max_context_tokens": 200000,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test OpenAI"
    assert data["provider"] == "openai"
    assert "api_key" not in data  # should not return plaintext key
    assert data["is_valid"] is False  # invalid key won't pass verification


@pytest.mark.asyncio
async def test_list_keys(client):
    await client.post("/api/keys", json={
        "name": "Key1", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    })
    await client.post("/api/keys", json={
        "name": "Key2", "provider": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key": "sk-2", "model": "claude-sonnet-4-20250514",
    })
    resp = await client.get("/api/keys")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_update_key(client):
    create_resp = await client.post("/api/keys", json={
        "name": "Old Name", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    })
    key_id = create_resp.json()["id"]

    resp = await client.put(f"/api/keys/{key_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_key(client):
    create_resp = await client.post("/api/keys", json={
        "name": "To Delete", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    })
    key_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/keys/{key_id}")
    assert resp.status_code == 200

    list_resp = await client.get("/api/keys")
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_activate_key(client):
    r1 = await client.post("/api/keys", json={
        "name": "Key1", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    })
    r2 = await client.post("/api/keys", json={
        "name": "Key2", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-2", "model": "gpt-4o",
    })
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Activate key1
    await client.post(f"/api/keys/{id1}/activate")
    keys = (await client.get("/api/keys")).json()
    active = [k for k in keys if k["is_active"]]
    assert len(active) == 1
    assert active[0]["id"] == id1

    # Activate key2 — key1 should deactivate
    await client.post(f"/api/keys/{id2}/activate")
    keys = (await client.get("/api/keys")).json()
    active = [k for k in keys if k["is_active"]]
    assert len(active) == 1
    assert active[0]["id"] == id2
