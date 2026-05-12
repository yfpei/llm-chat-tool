import pytest


async def _register(client, username, password):
    resp = await client.post("/api/auth/register", json={"username": username, "password": password})
    return resp.json()


@pytest.mark.asyncio
async def test_users_cannot_see_each_others_conversations(client):
    u1 = await _register(client, "alice", "alice1234")
    u2 = await _register(client, "bob", "bob5678")

    h1 = {"Authorization": f"Bearer {u1['access_token']}"}
    h2 = {"Authorization": f"Bearer {u2['access_token']}"}

    resp = await client.post("/api/conversations", json={"title": "Alice's chat"}, headers=h1)
    assert resp.status_code == 200

    resp = await client.get("/api/conversations", headers=h2)
    convs = resp.json()
    assert len(convs) == 0

    resp = await client.get("/api/conversations", headers=h1)
    convs = resp.json()
    assert len(convs) == 1
    assert convs[0]["title"] == "Alice's chat"


@pytest.mark.asyncio
async def test_admin_cannot_see_user_conversations(client):
    u1 = await _register(client, "boss", "admin123")
    u2 = await _register(client, "staff", "user1234")

    admin_headers = {"Authorization": f"Bearer {u1['access_token']}"}
    user_headers = {"Authorization": f"Bearer {u2['access_token']}"}

    await client.post("/api/conversations", json={"title": "private"}, headers=user_headers)

    resp = await client.get("/api/conversations", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_regular_user_cannot_access_user_management(client):
    u1 = await _register(client, "chief", "admin1234")
    u2 = await _register(client, "worker", "user1234")
    user_headers = {"Authorization": f"Bearer {u2['access_token']}"}

    resp = await client.get("/api/users", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_user_key_override(client):
    u1 = await _register(client, "key_admin", "admin1234")
    u2 = await _register(client, "key_user", "user1234")

    admin_headers = {"Authorization": f"Bearer {u1['access_token']}"}
    user_headers = {"Authorization": f"Bearer {u2['access_token']}"}

    resp = await client.post("/api/keys", json={
        "name": "shared-key",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test123",
        "model": "gpt-4o",
        "max_context_tokens": 200000,
        "enable_thinking": True,
    }, headers=admin_headers)
    assert resp.status_code == 200
    key_id = resp.json()["id"]

    resp = await client.get("/api/keys", headers=user_headers)
    keys = resp.json()
    assert len(keys) == 1
    assert keys[0]["user_id"] is None

    resp = await client.put(f"/api/keys/{key_id}/overrides", json={
        "enable_thinking": False,
        "max_context_tokens": 100000,
    }, headers=user_headers)
    assert resp.status_code == 200
