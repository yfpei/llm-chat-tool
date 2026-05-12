from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse,
    ApiKeyVerifyResponse, KeyOverrideRequest,
)
from app.services import key_service

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.post("", response_model=ApiKeyResponse)
async def create_key(
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Regular users create private keys (user_id=current_user.id)
    # Admins create shared keys (user_id=None)
    user_id = None if current_user.role == "admin" else current_user.id
    key = await key_service.create_key(db, data, user_id=user_id)
    return key


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await key_service.list_keys_for_user(db, current_user.id)


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_key(
    key_id: int,
    data: ApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = await key_service.get_key(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    # Check ownership: private keys only editable by owner, shared keys only by admin
    if key.user_id is not None and key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此 Key")
    if key.user_id is None and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="共享 Key 只能由管理员修改，你可以通过 /overrides 接口调整快慢思考和 Token 限制",
        )
    key = await key_service.update_key(db, key_id, data)
    return key


@router.delete("/{key_id}")
async def delete_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = await key_service.get_key(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    if key.user_id is not None and key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此 Key")
    if key.user_id is None and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="共享 Key 只能由管理员删除")
    await key_service.delete_key(db, key_id)
    return {"message": "deleted"}


@router.post("/{key_id}/verify", response_model=ApiKeyVerifyResponse)
async def verify_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = await key_service.get_key(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    if key.user_id is not None and key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此 Key")
    is_valid, message = await key_service.verify_key(db, key_id)
    return ApiKeyVerifyResponse(is_valid=is_valid, message=message)


@router.post("/{key_id}/activate", response_model=ApiKeyResponse)
async def activate_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = await key_service.activate_key(db, key_id, current_user)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return key


@router.put("/{key_id}/overrides")
async def set_key_overrides(
    key_id: int,
    data: KeyOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await key_service.upsert_key_override(
            db, key_id, current_user.id,
            enable_thinking=data.enable_thinking,
            max_context_tokens=data.max_context_tokens,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "override saved"}
