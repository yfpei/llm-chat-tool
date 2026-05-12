import logging

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey, UserKeyOverride
from app.schemas import ApiKeyCreate, ApiKeyUpdate
from app.utils.crypto import encrypt, decrypt

logger = logging.getLogger(__name__)


async def create_key(db: AsyncSession, data: ApiKeyCreate, user_id: int | None = None) -> ApiKey:
    key = ApiKey(
        name=data.name,
        provider=data.provider,
        base_url=data.base_url,
        api_key=encrypt(data.api_key),
        model=data.model,
        max_context_tokens=data.max_context_tokens,
        enable_thinking=data.enable_thinking,
        is_xinghuo_x1=data.is_xinghuo_x1,
        is_valid=False,
        is_active=False,
        user_id=user_id,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    # Try to verify
    is_valid, msg = await verify_key_connectivity(data.provider, data.base_url, data.api_key, data.model)
    logger.info("Key verify [%s] %s %s -> %s: %s", data.name, data.provider, data.base_url, is_valid, msg)
    key.is_valid = is_valid
    await db.commit()
    await db.refresh(key)
    return key


async def list_keys(db: AsyncSession) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())


async def list_keys_for_user(db: AsyncSession, user_id: int) -> list[ApiKey]:
    """Return shared keys (user_id=NULL) + user's own private keys."""
    result = await db.execute(
        select(ApiKey).where(
            or_(ApiKey.user_id == None, ApiKey.user_id == user_id)
        ).order_by(ApiKey.created_at.desc())
    )
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


async def activate_key(db: AsyncSession, key_id: int, user_id: int) -> ApiKey | None:
    key = await db.get(ApiKey, key_id)
    if not key:
        return None
    if key.user_id is not None and key.user_id != user_id:
        return None
    # Deactivate all keys visible to this user
    await db.execute(
        update(ApiKey).values(is_active=False).where(
            or_(ApiKey.user_id == user_id, ApiKey.user_id == None)
        )
    )
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
    logger.info("Key verify [id=%s] %s %s -> %s: %s", key_id, key.provider, key.base_url, is_valid, message)
    key.is_valid = is_valid
    await db.commit()
    return is_valid, message


async def verify_key_connectivity(provider: str, base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    """Verify that an API key is valid by making a test request."""
    import httpx

    base_url = base_url.rstrip("/")

    try:
        if provider == "openai":
            # 用 chat/completions 验证，兼容所有 OpenAI 协议代理
            url = f"{base_url}/chat/completions"
            logger.info("OpenAI verify -> POST %s", url)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                logger.info("OpenAI verify response: %s %s", resp.status_code, resp.text[:300])
                if resp.status_code == 200:
                    return True, "连接成功"
                body = resp.text[:200]
                return False, f"验证失败: HTTP {resp.status_code} - {body}"

        elif provider == "anthropic":
            # 智能拼接路径，避免 /v1/v1/messages
            if base_url.endswith("/v1"):
                messages_url = f"{base_url}/messages"
            else:
                messages_url = f"{base_url}/v1/messages"

            logger.info("Anthropic verify -> POST %s", messages_url)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    messages_url,
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
                body = resp.text[:200]
                return False, f"验证失败: HTTP {resp.status_code} - {body}"

        return False, f"未知的 provider: {provider}"

    except httpx.ConnectError as e:
        logger.error("ConnectError: %s", e)
        return False, "无法连接到服务器，请检查 Base URL 是否正确"
    except httpx.TimeoutException as e:
        logger.error("Timeout: %s", e)
        return False, "连接超时，请检查网络或 Base URL"
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return False, f"验证出错: {str(e)}"


def get_decrypted_key(key: ApiKey) -> str:
    return decrypt(key.api_key)


async def get_key_with_overrides(
    db: AsyncSession, key_id: int, user_id: int
) -> dict | None:
    """Return key data with user's effective override values."""
    key = await db.get(ApiKey, key_id)
    if not key:
        return None
    if key.user_id is not None and key.user_id != user_id:
        return None

    override = await db.execute(
        select(UserKeyOverride).where(
            UserKeyOverride.user_id == user_id,
            UserKeyOverride.api_key_id == key_id,
        )
    )
    override = override.scalar_one_or_none()

    return {
        "key": key,
        "effective_enable_thinking": override.enable_thinking if override and override.enable_thinking is not None else key.enable_thinking,
        "effective_max_context_tokens": override.max_context_tokens if override and override.max_context_tokens is not None else key.max_context_tokens,
    }


async def upsert_key_override(
    db: AsyncSession, key_id: int, user_id: int, enable_thinking: bool | None, max_context_tokens: int | None
) -> UserKeyOverride:
    key = await db.get(ApiKey, key_id)
    if not key:
        raise ValueError("Key not found")
    if key.user_id is not None and key.user_id != user_id:
        raise ValueError("Cannot override private keys")

    override = await db.execute(
        select(UserKeyOverride).where(
            UserKeyOverride.user_id == user_id,
            UserKeyOverride.api_key_id == key_id,
        )
    )
    override = override.scalar_one_or_none()

    if override is None:
        override = UserKeyOverride(
            user_id=user_id,
            api_key_id=key_id,
            enable_thinking=enable_thinking,
            max_context_tokens=max_context_tokens,
        )
        db.add(override)
    else:
        if enable_thinking is not None:
            override.enable_thinking = enable_thinking
        if max_context_tokens is not None:
            override.max_context_tokens = max_context_tokens
    await db.commit()
    await db.refresh(override)
    return override
