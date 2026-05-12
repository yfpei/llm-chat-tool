import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.utils.auth import hash_password, create_access_token, decode_access_token, verify_password


def test_hash_and_verify_password():
    h = hash_password("secret123")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_create_and_decode_token():
    token = create_access_token(1, "user")
    payload = decode_access_token(token)
    assert payload["sub"] == 1
    assert payload["role"] == "user"


def test_tampered_token_rejected():
    token = create_access_token(1, "user")
    with pytest.raises(Exception):
        decode_access_token(token + "x")


@pytest.mark.asyncio
async def test_register_first_user_is_admin(client):
    resp = await client.post("/api/auth/register", json={"username": "admin1", "password": "test1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    await client.post("/api/auth/register", json={"username": "dup", "password": "test1234"})
    resp = await client.post("/api/auth/register", json={"username": "dup", "password": "test1234"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/auth/register", json={"username": "login_test", "password": "test1234"})
    resp = await client.post("/api/auth/login", json={"username": "login_test", "password": "test1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={"username": "pwd_test", "password": "test1234"})
    resp = await client.post("/api/auth/login", json={"username": "pwd_test", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password(client):
    resp = await client.post("/api/auth/register", json={"username": "cp_test", "password": "old1234"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/auth/change-password", json={"old_password": "old1234", "new_password": "new5678"}, headers=headers)
    assert resp.status_code == 200

    resp = await client.post("/api/auth/login", json={"username": "cp_test", "password": "new5678"})
    assert resp.status_code == 200

    resp = await client.post("/api/auth/login", json={"username": "cp_test", "password": "old1234"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client):
    resp = await client.get("/api/conversations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_reset_password(client):
    resp = await client.post("/api/auth/register", json={"username": "adm", "password": "admin123"})
    admin_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await client.post("/api/users", json={"username": "victim", "password": "pass1234"}, headers=headers)
    assert resp.status_code == 200
    user_id = resp.json()["id"]

    resp = await client.post(f"/api/auth/reset-password/{user_id}", headers=headers)
    assert resp.status_code == 200
    new_pwd = resp.json()["new_password"]

    resp = await client.post("/api/auth/login", json={"username": "victim", "password": new_pwd})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_regular_user_cannot_reset_password(client):
    await client.post("/api/auth/register", json={"username": "adm2", "password": "admin123"})
    resp = await client.post("/api/auth/register", json={"username": "user2", "password": "user1234"})
    user_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    resp = await client.post("/api/auth/reset-password/1", headers=headers)
    assert resp.status_code == 403
