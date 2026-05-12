import pytest


async def _setup(client, username="key_test"):
    """Register a user and return auth headers."""
    resp = await client.post("/api/auth/register", json={"username": username, "password": "test1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_key(client):
    headers = await _setup(client)
    resp = await client.post("/api/keys", json={
        "name": "Test OpenAI",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-invalid-key",
        "model": "gpt-4o",
        "max_context_tokens": 200000,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test OpenAI"
    assert data["provider"] == "openai"
    assert "api_key" not in data
    assert data["is_valid"] is False


@pytest.mark.asyncio
async def test_list_keys(client):
    headers = await _setup(client)
    await client.post("/api/keys", json={
        "name": "Key1", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    }, headers=headers)
    await client.post("/api/keys", json={
        "name": "Key2", "provider": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key": "sk-2", "model": "claude-sonnet-4-20250514",
    }, headers=headers)
    resp = await client.get("/api/keys", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_update_key(client):
    headers = await _setup(client)
    create_resp = await client.post("/api/keys", json={
        "name": "Old Name", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    }, headers=headers)
    key_id = create_resp.json()["id"]

    resp = await client.put(f"/api/keys/{key_id}", json={"name": "New Name"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_key(client):
    headers = await _setup(client)
    create_resp = await client.post("/api/keys", json={
        "name": "To Delete", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    }, headers=headers)
    key_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/keys/{key_id}", headers=headers)
    assert resp.status_code == 200

    list_resp = await client.get("/api/keys", headers=headers)
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_activate_key(client):
    headers = await _setup(client)
    r1 = await client.post("/api/keys", json={
        "name": "Key1", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-1", "model": "gpt-4o",
    }, headers=headers)
    r2 = await client.post("/api/keys", json={
        "name": "Key2", "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-2", "model": "gpt-4o",
    }, headers=headers)
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    # Activate key1
    resp = await client.post(f"/api/keys/{id1}/activate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == id1

    # Activate key2 — should succeed and update user's active_key_id
    resp = await client.post(f"/api/keys/{id2}/activate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == id2
