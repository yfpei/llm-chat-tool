import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import User
from app.schemas import (
    LoginRequest, RegisterRequest, ChangePasswordRequest, AuthResponse,
)
from app.utils.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="用户已被禁用")
    token = create_access_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "role": user.role, "active_key_id": user.active_key_id},
    )


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if len(data.username) < 2 or len(data.username) > 50:
        raise HTTPException(status_code=400, detail="用户名长度为 2-50 个字符")
    if len(data.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少 4 个字符")

    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Check if this is the first user — make them admin
    count_result = await db.execute(select(User))
    is_first = len(count_result.scalars().all()) == 0

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role="admin" if is_first else "user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "role": user.role, "active_key_id": user.active_key_id},
    )


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少 4 个字符")
    current_user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "密码已修改"}


@router.post("/reset-password/{user_id}")
async def reset_password(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    new_password = secrets.token_urlsafe(8)
    user.password_hash = hash_password(new_password)
    await db.commit()
    return {"message": "密码已重置", "new_password": new_password}
