from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models import User
from app.schemas import UserResponse, UserCreate, UserUpdate
from app.utils.auth import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if len(data.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少 4 个字符")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.username is not None:
        existing = await db.execute(
            select(User).where(User.username == data.username, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = data.username
    if data.password is not None:
        user.password_hash = hash_password(data.password)
    # Remember original state before applying changes
    was_active_admin = user.role == "admin" and user.is_active
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    # Prevent disabling/demoting the last active admin
    if was_active_admin and (user.role != "admin" or not user.is_active):
        result = await db.execute(
            select(User).where(
                User.role == "admin",
                User.is_active == True,
                User.id != user_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="不能禁用或降级最后一个活跃管理员")
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        # Check if this is the last admin
        result = await db.execute(
            select(User).where(User.role == "admin", User.id != user_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="不能删除最后一个管理员")
    await db.delete(user)
    await db.commit()
    return {"message": "deleted"}
