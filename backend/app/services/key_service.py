from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey
from app.schemas import ApiKeyCreate, ApiKeyUpdate
from app.utils.crypto import encrypt, decrypt


async def create_key(db: AsyncSession, data: ApiKeyCreate) -> ApiKey:
    key = ApiKey(
        name=data.name,
        provider=data.provider,
        base_url=data.base_url,
        api_key=encrypt(data.api_key),
        model=data.model,
        max_context_tokens=data.max_context_tokens,
        is_valid=False,
        is_active=False,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    # Try to verify
    is_valid, _ = await verify_key_connectivity(data.provider, data.base_url, data.api_key, data.model)
    key.is_valid = is_valid
    await db.commit()
    await db.refresh(key)
    return key


async def list_keys(db: AsyncSession) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())


async def get_key(db: AsyncSession, key_id: int) -> ApiKey | None:
    return await db.get(ApiKey, key_id)


async def update_key(db: AsyncSession, key_id: int, data: ApiKeyUpdate) -> ApiKey | None:
    key = await db.get(ApiKey, key_id)
    if not key:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if "api_key" in update_data:
        update_data["api_key"] = encrypt(update_data["api_key"])
    for field, value in update_data.items():
        setattr(key, field, value)
    await db.commit()
    await db.refresh(key)
    return key


async def delete_key(db: AsyncSession, key_id: int) -> bool:
    key = await db.get(ApiKey, key_id)
    if not key:
        return False
    await db.delete(key)
    await db.commit()
    return True


async def activate_key(db: AsyncSession, key_id: int) -> ApiKey | None:
    key = await db.get(ApiKey, key_id)
    if not key:
        return None
    # Deactivate all
    await db.execute(update(ApiKey).values(is_active=False))
    # Activate this one
    key.is_active = True
    await db.commit()
    await db.refresh(key)
    return key


async def verify_key(db: AsyncSession, key_id: int) -> tuple[bool, str]:
    key = await db.get(ApiKey, key_id)
    if not key:
        return False, "Key not found"
    plaintext_key = decrypt(key.api_key)
    is_valid, message = await verify_key_connectivity(key.provider, key.base_url, plaintext_key, key.model)
    key.is_valid = is_valid
    await db.commit()
    return is_valid, message


async def verify_key_connectivity(provider: str, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    """Verify that an API key is valid by making a test request."""
    import httpx

    try:
        if provider == "openai":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 200:
                    return True, "连接成功"
                return False, f"验证失败: HTTP {resp.status_code}"

        elif provider == "anthropic":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{base_url}/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                if resp.status_code == 200:
                    return True, "连接成功"
                return False, f"验证失败: HTTP {resp.status_code}"

        return False, f"未知的 provider: {provider}"

    except httpx.ConnectError:
        return False, "无法连接到服务器"
    except httpx.TimeoutException:
        return False, "连接超时"
    except Exception as e:
        return False, f"验证出错: {str(e)}"


def get_decrypted_key(key: ApiKey) -> str:
    return decrypt(key.api_key)
