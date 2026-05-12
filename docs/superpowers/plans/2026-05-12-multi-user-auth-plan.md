# Multi-User Auth & Permission Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-user support (up to 10 users) with admin/user roles, JWT auth, data isolation, and mixed API key management to the existing LLM Chat Tool.

**Architecture:** Backend adds User + UserKeyOverride models, JWT auth middleware, and user_id filtering on all business queries. Frontend adds vue-router with auth guards, login/register/admin pages, and shared/private key distinction in SettingsPanel. No new infrastructure — stays on SQLite.

**Tech Stack:** FastAPI + SQLAlchemy (async) + SQLite + PyJWT + passlib | Vue 3 + Pinia + Naive UI + vue-router

---

## File Structure

### Backend — Create
- `backend/app/utils/auth.py` — JWT encode/decode + password hash/verify
- `backend/app/deps.py` — get_current_user dependency + optional get_optional_user
- `backend/app/routers/auth.py` — login, register, change-password, reset-password endpoints
- `backend/app/routers/users.py` — admin user CRUD endpoints
- `backend/tests/test_auth.py` — JWT + auth endpoint tests
- `backend/tests/test_isolation.py` — data isolation + permission tests

### Backend — Modify
- `backend/app/models.py` — add User, UserKeyOverride models; add user_id to existing models
- `backend/app/database.py` — migration logic in init_db
- `backend/app/schemas.py` — auth/user/key schemas
- `backend/app/main.py` — include new routers
- `backend/app/routers/conversations.py` — user_id filtering
- `backend/app/routers/chat.py` — user_id filtering
- `backend/app/routers/batch.py` — user_id filtering
- `backend/app/routers/batch_tasks.py` — user_id filtering
- `backend/app/routers/es_export.py` — user_id filtering
- `backend/app/routers/keys.py` — shared/private key + override logic
- `backend/app/services/key_service.py` — override resolution, user-scoped queries
- `backend/requirements.txt` — add PyJWT, passlib[bcrypt]

### Frontend — Create
- `frontend/src/router/index.ts` — route definitions + auth/admin guards
- `frontend/src/stores/auth.ts` — auth state, login/logout/register actions
- `frontend/src/api/client.ts` — fetch wrapper with auth header injection + 401 interception
- `frontend/src/api/auth.ts` — login/register/change-password API calls
- `frontend/src/api/users.ts` — admin user CRUD API calls
- `frontend/src/views/LoginPage.vue` — login form
- `frontend/src/views/RegisterPage.vue` — register form
- `frontend/src/views/AdminUsersPage.vue` — admin user management table
- `frontend/src/views/ChangePasswordPage.vue` — change password form

### Frontend — Modify
- `frontend/src/main.ts` — register router
- `frontend/src/App.vue` — replace KeepAlive with router-view, add user menu in sidebar
- `frontend/src/components/SettingsPanel.vue` — split keys into Shared/My Keys, add override controls
- `frontend/src/api/conversations.ts` — use authFetch
- `frontend/src/api/keys.ts` — use authFetch, add override endpoints
- `frontend/src/api/chat.ts` — use authFetch
- `frontend/src/api/batch.ts` — use authFetch
- `frontend/src/api/batchTasks.ts` — use authFetch
- `frontend/src/api/esExport.ts` — use authFetch
- `frontend/src/types/index.ts` — add auth/user types

---

## Phase 1: Backend Foundation

### Task 1: Install Python dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add PyJWT and passlib to requirements.txt**

Edit `backend/requirements.txt`, add two lines at the end:
```
PyJWT>=2.8.0
passlib[bcrypt]>=1.7.4
```

- [ ] **Step 2: Install dependencies**

Run: `cd /mnt/d/zhcs/model-web/backend && pip install PyJWT "passlib[bcrypt]"`

Expected: packages install successfully.

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: add PyJWT and passlib for authentication"
```

---

### Task 2: Add User and UserKeyOverride models + user_id columns

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add new models and modify existing ones**

Edit `backend/app/models.py`, add after the existing imports:

```python
# Add this import at the top, after the existing imports
from sqlalchemy import UniqueConstraint
```

Replace the entire file content after line 7:

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(10), nullable=False, default="user")  # "admin" or "user"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    api_keys = relationship("ApiKey", back_populates="owner")
    conversations = relationship("Conversation", back_populates="user")
    batch_tasks = relationship("BatchTask", back_populates="user")
    es_export_tasks = relationship("EsExportTask", back_populates="user")
    key_overrides = relationship("UserKeyOverride", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(20), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    max_context_tokens = Column(Integer, default=200000)
    enable_thinking = Column(Boolean, default=True)
    is_xinghuo_x1 = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    is_valid = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="api_keys")
    conversations = relationship("Conversation", back_populates="api_key_rel")
    overrides = relationship("UserKeyOverride", back_populates="api_key", cascade="all, delete-orphan")


class UserKeyOverride(Base):
    __tablename__ = "user_key_overrides"
    __table_args__ = (UniqueConstraint("user_id", "api_key_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    enable_thinking = Column(Boolean, nullable=True)
    max_context_tokens = Column(Integer, nullable=True)

    user = relationship("User", back_populates="key_overrides")
    api_key = relationship("ApiKey", back_populates="overrides")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), default="新会话")
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    api_key_rel = relationship("ApiKey", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class BatchTask(Base):
    __tablename__ = "batch_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), default="未命名任务")
    file_id = Column(String(36), nullable=False)
    filename = Column(String(500), nullable=False)
    columns = Column(Text, nullable=False)
    headers = Column(Text, nullable=False)
    total_rows = Column(Integer, default=0)
    status = Column(String(20), default="uploaded")
    config_json = Column(Text, nullable=True)
    progress_completed = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="batch_tasks")


class EsExportTask(Base):
    __tablename__ = "es_export_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), default="未命名导出任务")
    es_host = Column(String(500), nullable=False)
    es_username = Column(String(100), nullable=True)
    es_password = Column(Text, nullable=True)
    index_name = Column(String(200), nullable=True)
    query_dsl = Column(Text, nullable=True)
    output_fields = Column(Text, nullable=True)
    status = Column(String(20), default="created")
    total_hits = Column(Integer, default=0)
    exported_count = Column(Integer, default=0)
    file_id = Column(String(36), nullable=True)
    config_json = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="es_export_tasks")
```

- [ ] **Step 2: Verify models import correctly**

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "from app.models import User, ApiKey, UserKeyOverride, Conversation, Message, BatchTask, EsExportTask; print('All models OK')"`

Expected: `All models OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add User and UserKeyOverride models with user_id columns"
```

---

### Task 3: Create JWT and password utilities

**Files:**
- Create: `backend/app/utils/auth.py`

- [ ] **Step 1: Write auth utility module**

Create `backend/app/utils/auth.py`:

```python
import os
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

- [ ] **Step 2: Verify the utility works**

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "
from app.utils.auth import hash_password, verify_password, create_access_token, decode_access_token
h = hash_password('test123')
assert verify_password('test123', h)
assert not verify_password('wrong', h)
t = create_access_token(1, 'user')
d = decode_access_token(t)
assert d['sub'] == 1
assert d['role'] == 'user'
print('All auth utils OK')
"`

Expected: `All auth utils OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/utils/auth.py
git commit -m "feat: add JWT and password utility functions"
```

---

### Task 4: Create get_current_user dependency

**Files:**
- Create: `backend/app/deps.py`

- [ ] **Step 1: Write dependencies module**

Create `backend/app/deps.py`:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.utils.auth import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期，请重新登录",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效")
    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
```

- [ ] **Step 2: Verify the module imports**

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "from app.deps import get_current_user, require_admin; print('deps OK')"`

Expected: `deps OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/deps.py
git commit -m "feat: add get_current_user and require_admin dependencies"
```

---

### Task 5: Create auth schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add auth and user schemas**

Edit `backend/app/schemas.py`, add these new schemas before the existing `# --- API Key Schemas ---` line:

```python
# --- Auth Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AuthResponse(BaseModel):
    access_token: str
    user: dict  # { id, username, role }


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


# --- Key Override Schemas ---
class KeyOverrideRequest(BaseModel):
    enable_thinking: bool | None = None
    max_context_tokens: int | None = None


class KeyWithOverridesResponse(ApiKeyResponse):
    owner_username: str | None = None
    user_enable_thinking: bool | None = None
    user_max_context_tokens: int | None = None
```

Also update `ApiKeyResponse` to include `user_id`:

In the `ApiKeyResponse` class, add the line:
```python
    user_id: Optional[int] = None
```

- [ ] **Step 2: Verify schemas import**

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "from app.schemas import LoginRequest, RegisterRequest, AuthResponse, UserResponse, UserCreate, KeyOverrideRequest, KeyWithOverridesResponse; print('Schemas OK')"`

Expected: `Schemas OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: add auth, user, and key override schemas"
```

---

### Task 6: Create auth router (login, register, change-password, reset-password)

**Files:**
- Create: `backend/app/routers/auth.py`

- [ ] **Step 1: Write auth router**

Create `backend/app/routers/auth.py`:

```python
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
        user={"id": user.id, "username": user.username, "role": user.role},
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
        user={"id": user.id, "username": user.username, "role": user.role},
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/auth.py
git commit -m "feat: add auth router with login, register, change-password, reset-password"
```

---

### Task 7: Create admin users router

**Files:**
- Create: `backend/app/routers/users.py`

- [ ] **Step 1: Write users router**

Create `backend/app/routers/users.py`:

```python
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
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/users.py
git commit -m "feat: add admin user management router"
```

---

### Task 8: Update database init and wire up routers in main.py

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update database init for new tables and migrations**

Edit `backend/app/database.py`, replace the `init_db` function:

```python
async def init_db():
    from sqlalchemy import text

    async with engine.begin() as conn:
        from app.models import User, ApiKey, UserKeyOverride, Conversation, Message, BatchTask, EsExportTask  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

        # --- Migrations for existing databases ---

        # Add is_xinghuo_x1 column
        try:
            await conn.execute(text("ALTER TABLE api_keys ADD COLUMN is_xinghuo_x1 BOOLEAN DEFAULT 0"))
        except Exception:
            pass

        # Add user_id to api_keys
        try:
            await conn.execute(text("ALTER TABLE api_keys ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass

        # Add user_id to conversations
        try:
            await conn.execute(text("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass

        # Add user_id to batch_tasks
        try:
            await conn.execute(text("ALTER TABLE batch_tasks ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass

        # Add user_id to es_export_tasks
        try:
            await conn.execute(text("ALTER TABLE es_export_tasks ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        except Exception:
            pass
```

- [ ] **Step 2: Wire up new routers in main.py**

Edit `backend/app/main.py`, add the two new router imports (change the existing import line):

```python
from app.routers import keys, conversations, chat, batch, batch_tasks, es_export, auth, users
```

And add the router includes after the existing ones:

```python
app.include_router(auth.router)
app.include_router(users.router)
```

- [ ] **Step 3: Verify app starts**

Run: `cd /mnt/d/zhcs/model-web/backend && timeout 5 python -c "
import asyncio
from app.main import app
print('App creates OK')
" 2>&1 || true`

Expected: `App creates OK` (ignore any warnings)

- [ ] **Step 4: Commit**

```bash
git add backend/app/database.py backend/app/main.py
git commit -m "feat: update database init for auth tables and wire up auth/users routers"
```

---

## Phase 2: Backend Data Isolation

### Task 9: Modify conversations router for user isolation

**Files:**
- Modify: `backend/app/routers/conversations.py`

- [ ] **Step 1: Add user filtering to all endpoints**

Edit `backend/app/routers/conversations.py`, add imports and modify all endpoints:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models import Conversation, User
from app.schemas import (
    ConversationCreate, ConversationUpdate,
    ConversationResponse, ConversationDetailResponse,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = Conversation(
        title=data.title,
        api_key_id=data.api_key_id,
        user_id=current_user.id,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conv_id, Conversation.user_id == current_user.id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.put("/{conv_id}", response_model=ConversationResponse)
async def update_conversation(
    conv_id: str,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conv, field, value)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == current_user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    return {"message": "deleted"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/conversations.py
git commit -m "feat: add user isolation to conversations endpoints"
```

---

### Task 10: Modify chat router for user isolation

**Files:**
- Modify: `backend/app/routers/chat.py`

- [ ] **Step 1: Add user isolation to chat endpoint**

Edit `backend/app/routers/chat.py`. Change the import block at the top to add `select`, `get_current_user`, and `User`:

```python
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db, async_session
from app.deps import get_current_user
from app.models import Message, Conversation, User
from app.schemas import ChatRequest
from app.services.chat_service import get_conversation_with_key, truncate_messages
from app.services.llm import create_provider
from app.services.key_service import get_decrypted_key
```

Replace the `chat` function signature and the conversation lookup:

```python
@router.post("/{conversation_id}")
async def chat(
    conversation_id: str,
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv, api_key = await get_conversation_with_key(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key，请先添加并激活一个 API Key")
```

Leave the rest of the function body unchanged.

- [ ] **Step 2: Verify chat router imports**

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "from app.routers.chat import router; print('chat router OK')"`

Expected: `chat router OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/chat.py
git commit -m "feat: add user isolation to chat endpoint"
```

---

### Task 11: Modify batch and batch_tasks routers for user isolation

**Files:**
- Modify: `backend/app/routers/batch.py`
- Modify: `backend/app/routers/batch_tasks.py`

- [ ] **Step 1: Modify batch.py upload and run endpoints**

Edit `backend/app/routers/batch.py`. Add to the existing imports (after the `from app.database import get_db` line):
```python
from app.deps import get_current_user
from app.models import User
```

Modify `upload_excel` — add `current_user` parameter and set `user_id` on new and re-upload tasks. The function signature becomes:
```python
async def upload_excel(
    file: UploadFile = File(...),
    task_id: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
```

When creating a new `BatchTask(...)`, add `user_id=current_user.id` to the constructor. In the re-upload branch (the `if task_id:` block), add after the existence check:
```python
if task.user_id != current_user.id:
    os.remove(xlsx_path)
    raise HTTPException(status_code=404, detail="任务不存在")
```

Modify `run_batch` — add `current_user` parameter and verify ownership:
```python
async def run_batch(
    req: BatchRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, req.task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        ...
```

Modify `filter_preview_endpoint` — add `current_user` and verify:
```python
async def filter_preview_endpoint(
    task_id: str,
    filter_config: FilterConfig | None = Body(None),
    current_user: User = Depends(get_current_user),
):
    ...
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
```

Modify `download_filtered` — add `current_user` and verify same as above.

Modify `download_result` — add `current_user: User = Depends(get_current_user)` and verify ownership.

- [ ] **Step 2: Modify batch_tasks.py**

Edit `backend/app/routers/batch_tasks.py`. Replace the entire file content:

```python
import json
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import BatchTask, User
from app.schemas import BatchTaskUpdate, BatchTaskResponse
from app.services import batch_service
from app.services.batch_service import UPLOAD_DIR

router = APIRouter(prefix="/api/batch-tasks", tags=["batch-tasks"])


def _resolve_file_path(file_id: str) -> str:
    result_path = os.path.join(UPLOAD_DIR, f"{file_id}_result.xlsx")
    if os.path.exists(result_path):
        return result_path
    return os.path.join(UPLOAD_DIR, f"{file_id}.xlsx")


def _verify_ownership(task: BatchTask | None, current_user: User):
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.get("", response_model=list[BatchTaskResponse])
async def list_batch_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BatchTask)
        .where(BatchTask.user_id == current_user.id)
        .order_by(BatchTask.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=BatchTaskResponse)
async def get_batch_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    return task


@router.put("/{task_id}", response_model=BatchTaskResponse)
async def update_batch_task(
    task_id: str,
    data: BatchTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}/preview")
async def get_task_preview(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    file_path = _resolve_file_path(task.file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    info = batch_service.parse_upload(file_path)
    return {"columns": info["columns"], "headers": info["headers"], "total_rows": info["total_rows"], "preview": info["preview"]}


@router.get("/{task_id}/results")
async def get_task_results(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    file_path = _resolve_file_path(task.file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(c) if c is not None else "" for c in next(rows_iter, [])]

    input_col_indices: dict[str, int] = {}
    output_col_idx = len(headers) - 1
    parse_json_enabled = False
    if task.config_json:
        try:
            cfg = json.loads(task.config_json)
            input_cols = cfg.get("input_columns")
            if not input_cols:
                input_col = cfg.get("input_column", "")
                input_cols = [input_col] if input_col else []
            for col_name in input_cols:
                if col_name in headers:
                    input_col_indices[col_name] = headers.index(col_name)
            output_col = cfg.get("output_column_name", "")
            if output_col in headers:
                output_col_idx = headers.index(output_col)
            parse_json_enabled = cfg.get("parse_json", False)
        except (json.JSONDecodeError, ValueError):
            pass

    parsed_field_cols: list[tuple[int, str]] = []
    if parse_json_enabled and output_col_idx < len(headers):
        for i in range(output_col_idx + 1, len(headers)):
            parsed_field_cols.append((i, headers[i]))

    def build_input_label(row: tuple) -> str:
        parts = []
        for col_name, ci in input_col_indices.items():
            val = str(row[ci]) if ci < len(row) and row[ci] is not None else ""
            parts.append(f"{col_name}: {val}")
        return "; ".join(parts)

    results = []
    for row_idx, row in enumerate(rows_iter, start=2):
        input_val = build_input_label(row)
        output_val = str(row[output_col_idx]) if output_col_idx < len(row) and row[output_col_idx] is not None else ""
        item: dict = {
            "row": row_idx,
            "input": input_val,
            "output": output_val,
            "status": "success" if output_val else "error",
        }
        if parsed_field_cols:
            parsed: dict[str, str] = {}
            for ci, name in parsed_field_cols:
                val = row[ci] if ci < len(row) and row[ci] is not None else ""
                parsed[name] = str(val)
            if any(v for v in parsed.values()):
                item["parsed"] = parsed
        results.append(item)

    wb.close()
    return results


@router.delete("/{task_id}")
async def delete_batch_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(BatchTask, task_id)
    _verify_ownership(task, current_user)
    for suffix in (".xlsx", "_original.xlsx", "_result.xlsx"):
        p = os.path.join(UPLOAD_DIR, f"{task.file_id}{suffix}")
        if os.path.exists(p):
            os.remove(p)
    await db.delete(task)
    await db.commit()
    return {"message": "deleted"}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/batch.py backend/app/routers/batch_tasks.py
git commit -m "feat: add user isolation to batch and batch_tasks routers"
```

---

### Task 12: Modify es_export router for user isolation

**Files:**
- Modify: `backend/app/routers/es_export.py`

- [ ] **Step 1: Add user isolation**

Edit `backend/app/routers/es_export.py`. Update the imports to add `select`, `get_current_user`, and `User`:

In the existing import block, change:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models import EsExportTask
```
to:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.deps import get_current_user
from app.models import EsExportTask, User
```

Add a helper function after `_get_password`:

```python
def _verify_ownership(task: EsExportTask | None, current_user: User):
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
```

Then modify each endpoint function to add `current_user: User = Depends(get_current_user)` parameter and call `_verify_ownership(task, current_user)` after each `task = await db.get(EsExportTask, task_id)`.

For `create_task`, also set `user_id=current_user.id` on the new task:

```python
task = EsExportTask(
    title=data.title,
    es_host=data.es_host,
    es_username=data.es_username,
    es_password=encrypt(data.es_password) if data.es_password else None,
    status="created",
    user_id=current_user.id,
)
```

For `list_tasks`, add the user filter:
```python
result = await db.execute(
    select(EsExportTask)
    .where(EsExportTask.user_id == current_user.id)
    .order_by(EsExportTask.created_at.desc())
)
```

- [ ] **Step 2: Verify imports**

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "from app.routers.es_export import router; print('es_export router OK')"`

Expected: `es_export router OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/es_export.py
git commit -m "feat: add user isolation to es_export router"
```

---

### Task 13: Modify keys router and key_service for shared/private + overrides

**Files:**
- Modify: `backend/app/routers/keys.py`
- Modify: `backend/app/services/key_service.py`

- [ ] **Step 1: Update key_service for user-scoped queries and override logic**

Edit `backend/app/services/key_service.py`, replace the `list_keys` function and add new functions:

```python
async def list_keys_for_user(db: AsyncSession, user_id: int) -> list[ApiKey]:
    """Return shared keys (user_id=NULL) + user's own private keys."""
    from sqlalchemy import or_
    result = await db.execute(
        select(ApiKey).where(
            or_(ApiKey.user_id == None, ApiKey.user_id == user_id)
        ).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())
```

Add override functions:

```python
from app.models import UserKeyOverride


async def get_key_with_overrides(
    db: AsyncSession, key_id: int, user_id: int
) -> dict | None:
    """Return key data with user's effective override values."""
    from sqlalchemy import or_
    key = await db.get(ApiKey, key_id)
    if not key:
        return None
    # Check access
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
    from sqlalchemy import or_
    # Verify key is shared and user has access
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
```

Modify `activate_key` to be user-scoped (only deactivate for this user's active key, not globally). Actually, let's keep activation simple — "active" is a user-level concept now. Replace `activate_key`:

```python
async def activate_key(db: AsyncSession, key_id: int, user_id: int) -> ApiKey | None:
    from sqlalchemy import or_
    key = await db.get(ApiKey, key_id)
    if not key:
        return None
    # Check access
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
```

Modify `create_key` to accept `user_id` parameter:

```python
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

    is_valid, msg = await verify_key_connectivity(data.provider, data.base_url, data.api_key, data.model)
    logger.info("Key verify [%s] %s %s -> %s: %s", data.name, data.provider, data.base_url, is_valid, msg)
    key.is_valid = is_valid
    await db.commit()
    await db.refresh(key)
    return key
```

- [ ] **Step 2: Update keys router**

Edit `backend/app/routers/keys.py`, replace all endpoints with user-scoped versions:

```python
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
        # Regular user trying to edit shared key — only allow enable_thinking and max_context_tokens
        # (handled via /overrides endpoint instead)
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
    success = await key_service.delete_key(db, key_id)
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
    key = await key_service.activate_key(db, key_id, current_user.id)
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
```

- [ ] **Step 3: Verify module imports**

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "from app.services.key_service import list_keys_for_user, get_key_with_overrides, upsert_key_override; print('key_service OK')"`

Run: `cd /mnt/d/zhcs/model-web/backend && python -c "from app.routers.keys import router; print('keys router OK')"`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/keys.py backend/app/services/key_service.py
git commit -m "feat: add user-scoped key management with shared/private keys and overrides"
```

---

## Phase 3: Backend Tests

### Task 14: Write auth tests

**Files:**
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write auth test file**

Create `backend/tests/test_auth.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, async_session
from app.models import User
from app.utils.auth import hash_password, create_access_token, decode_access_token, verify_password
from sqlalchemy import select


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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

    # Change password
    resp = await client.post("/api/auth/change-password", json={"old_password": "old1234", "new_password": "new5678"}, headers=headers)
    assert resp.status_code == 200

    # Login with new password works
    resp = await client.post("/api/auth/login", json={"username": "cp_test", "password": "new5678"})
    assert resp.status_code == 200

    # Old password fails
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

    # Create a user
    resp = await client.post("/api/users", json={"username": "victim", "password": "pass1234"}, headers=headers)
    assert resp.status_code == 200
    user_id = resp.json()["id"]

    # Reset their password
    resp = await client.post(f"/api/auth/reset-password/{user_id}", headers=headers)
    assert resp.status_code == 200
    new_pwd = resp.json()["new_password"]

    # Victim can login with new password
    resp = await client.post("/api/auth/login", json={"username": "victim", "password": new_pwd})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_regular_user_cannot_reset_password(client):
    # Register regular user (second user)
    await client.post("/api/auth/register", json={"username": "adm2", "password": "admin123"})
    resp = await client.post("/api/auth/register", json={"username": "user2", "password": "user1234"})
    user_token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {user_token}"}

    resp = await client.post("/api/auth/reset-password/1", headers=headers)
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests**

Run: `cd /mnt/d/zhcs/model-web/backend && python -m pytest tests/test_auth.py -v`

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_auth.py
git commit -m "test: add auth endpoint tests"
```

---

### Task 15: Write data isolation and permission tests

**Files:**
- Create: `backend/tests/test_isolation.py`

- [ ] **Step 1: Write isolation tests**

Create `backend/tests/test_isolation.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register(client, username, password):
    resp = await client.post("/api/auth/register", json={"username": username, "password": password})
    return resp.json()


@pytest.mark.asyncio
async def test_users_cannot_see_each_others_conversations(client):
    # Create two users
    u1 = await _register(client, "alice", "alice1234")
    u2 = await _register(client, "bob", "bob5678")

    h1 = {"Authorization": f"Bearer {u1['access_token']}"}
    h2 = {"Authorization": f"Bearer {u2['access_token']}"}

    # Alice creates a conversation
    resp = await client.post("/api/conversations", json={"title": "Alice's chat"}, headers=h1)
    assert resp.status_code == 200

    # Bob sees empty list
    resp = await client.get("/api/conversations", headers=h2)
    convs = resp.json()
    assert len(convs) == 0

    # Alice sees her conversation
    resp = await client.get("/api/conversations", headers=h1)
    convs = resp.json()
    assert len(convs) == 1
    assert convs[0]["title"] == "Alice's chat"


@pytest.mark.asyncio
async def test_admin_cannot_manage_users(client):
    # First user is admin
    u1 = await _register(client, "admin_test", "admin1234")
    admin_headers = {"Authorization": f"Bearer {u1['access_token']}"}

    # Admin creates a user
    resp = await client.post("/api/users", json={"username": "normal_user", "password": "pass1234"}, headers=admin_headers)
    assert resp.status_code == 200

    # Admin lists users
    resp = await client.get("/api/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 2


@pytest.mark.asyncio
async def test_regular_user_cannot_access_user_management(client):
    # First user (admin)
    await _register(client, "chief", "admin1234")
    # Second user (regular)
    u2 = await _register(client, "worker", "user1234")
    user_headers = {"Authorization": f"Bearer {u2['access_token']}"}

    resp = await client.get("/api/users", headers=user_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_see_user_conversations(client):
    u1 = await _register(client, "boss", "admin1234")
    u2 = await _register(client, "staff", "user1234")

    admin_headers = {"Authorization": f"Bearer {u1['access_token']}"}
    user_headers = {"Authorization": f"Bearer {u2['access_token']}"}

    # Staff creates a conversation
    await client.post("/api/conversations", json={"title": "private"}, headers=user_headers)

    # Admin cannot see it
    resp = await client.get("/api/conversations", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_user_key_override(client):
    u1 = await _register(client, "key_admin", "admin1234")
    u2 = await _register(client, "key_user", "user1234")

    admin_headers = {"Authorization": f"Bearer {u1['access_token']}"}
    user_headers = {"Authorization": f"Bearer {u2['access_token']}"}

    # Admin creates a shared key
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

    # User sees the shared key
    resp = await client.get("/api/keys", headers=user_headers)
    keys = resp.json()
    assert len(keys) == 1
    assert keys[0]["user_id"] is None

    # User sets override on enable_thinking
    resp = await client.put(f"/api/keys/{key_id}/overrides", json={
        "enable_thinking": False,
        "max_context_tokens": 100000,
    }, headers=user_headers)
    assert resp.status_code == 200
```

- [ ] **Step 2: Run isolation tests**

Run: `cd /mnt/d/zhcs/model-web/backend && python -m pytest tests/test_isolation.py -v`

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_isolation.py
git commit -m "test: add data isolation and permission tests"
```

---

## Phase 4: Frontend Foundation

### Task 16: Install vue-router and create router with guards

**Files:**
- Create: `frontend/src/router/index.ts`
- Modify: `frontend/src/main.ts`

- [ ] **Step 1: Install vue-router**

Run: `cd /mnt/d/zhcs/model-web/frontend && npm install vue-router`

- [ ] **Step 2: Create router file**

Create `frontend/src/router/index.ts`:

```typescript
import { createRouter, createWebHistory } from 'vue-router'

function getToken(): string | null {
  return localStorage.getItem('token')
}

function getUser(): { role: string } | null {
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginPage.vue'),
      meta: { guest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterPage.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      redirect: '/chat',
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/ChatPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/batch',
      name: 'batch',
      component: () => import('../views/BatchPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/es-export',
      name: 'es-export',
      component: () => import('../views/EsExportPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('../views/AdminUsersPage.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/settings/password',
      name: 'change-password',
      component: () => import('../views/ChangePasswordPage.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = getToken()

  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }

  if (to.meta.guest && token) {
    next('/chat')
    return
  }

  if (to.meta.requiresAdmin) {
    const user = getUser()
    if (!user || user.role !== 'admin') {
      next('/chat')
      return
    }
  }

  next()
})

export default router
```

- [ ] **Step 3: Add router to main.ts**

Edit `frontend/src/main.ts`, replace with:

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.ts frontend/src/router/index.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: add vue-router with auth and admin guards"
```

---

### Task 17: Create auth store and API client

**Files:**
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/api/client.ts`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add auth types**

Edit `frontend/src/types/index.ts`, add at the top:

```typescript
export interface AuthUser {
  id: number
  username: string
  role: 'admin' | 'user'
}

export interface AuthResponse {
  access_token: string
  user: AuthUser
}

export interface UserInfo {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
}
```

- [ ] **Step 2: Create auth store**

Create `frontend/src/stores/auth.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AuthUser } from '../types'
import * as authApi from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const token = ref<string | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function _loadFromStorage() {
    const savedToken = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    if (savedToken && savedUser) {
      token.value = savedToken
      try {
        user.value = JSON.parse(savedUser)
      } catch {
        _clear()
      }
    }
  }

  function _saveToStorage(t: string, u: AuthUser) {
    token.value = t
    user.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('user', JSON.stringify(u))
  }

  function _clear() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function login(username: string, password: string) {
    const resp = await authApi.login(username, password)
    _saveToStorage(resp.access_token, resp.user)
    return resp.user
  }

  async function register(username: string, password: string) {
    const resp = await authApi.register(username, password)
    _saveToStorage(resp.access_token, resp.user)
    return resp.user
  }

  function logout() {
    _clear()
  }

  // Initialize from storage on store creation
  _loadFromStorage()

  return { user, token, isLoggedIn, isAdmin, login, register, logout }
})
```

- [ ] **Step 3: Create API client with auth header**

Create `frontend/src/api/client.ts`:

```typescript
export function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return fetch(url, { ...options, headers }).then((resp) => {
    if (resp.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return resp
  })
}
```

- [ ] **Step 4: Create auth API layer**

Create `frontend/src/api/auth.ts`:

```typescript
import type { AuthResponse } from '../types'

export async function login(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '登录失败')
  }
  return res.json()
}

export async function register(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '注册失败')
  }
  return res.json()
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const token = localStorage.getItem('token')
  const res = await fetch('/api/auth/change-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '修改密码失败')
  }
}
```

- [ ] **Step 5: Create users API layer**

Create `frontend/src/api/users.ts`:

```typescript
import { authFetch } from './client'
import type { UserInfo } from '../types'

export async function fetchUsers(): Promise<UserInfo[]> {
  const res = await authFetch('/api/users')
  return res.json()
}

export async function createUser(data: { username: string; password: string; role: string }): Promise<UserInfo> {
  const res = await authFetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '创建用户失败')
  }
  return res.json()
}

export async function updateUser(id: number, data: Record<string, unknown>): Promise<UserInfo> {
  const res = await authFetch(`/api/users/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '更新用户失败')
  }
  return res.json()
}

export async function deleteUser(id: number): Promise<void> {
  await authFetch(`/api/users/${id}`, { method: 'DELETE' })
}

export async function resetUserPassword(id: number): Promise<string> {
  const res = await authFetch(`/api/auth/reset-password/${id}`, { method: 'POST' })
  const data = await res.json()
  return data.new_password
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/auth.ts frontend/src/api/client.ts frontend/src/api/auth.ts frontend/src/api/users.ts frontend/src/types/index.ts
git commit -m "feat: add auth store, API client, and auth/users API layers"
```

---

### Task 18: Create LoginPage and RegisterPage

**Files:**
- Create: `frontend/src/views/LoginPage.vue`
- Create: `frontend/src/views/RegisterPage.vue`

- [ ] **Step 1: Create LoginPage**

Create `frontend/src/views/LoginPage.vue`:

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1>登录 LLM Chat</h1>
      </div>
      <n-form :model="form" label-placement="top">
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" placeholder="输入用户名" size="large" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="输入密码" size="large" @keyup.enter="handleLogin" />
        </n-form-item>
        <n-button type="primary" block size="large" :loading="loading" @click="handleLogin">登录</n-button>
      </n-form>
      <div class="auth-switch">
        还没有账号？<router-link to="/register">注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const message = useMessage()
const loading = ref(false)

const form = reactive({ username: '', password: '' })

async function handleLogin() {
  if (!form.username || !form.password) {
    message.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/chat')
  } catch (e: any) {
    message.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f5f5f7;
}
.auth-card {
  width: 380px;
  background: #fff;
  border-radius: 16px;
  padding: 36px 32px 28px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.06);
}
.auth-header {
  text-align: center;
  margin-bottom: 28px;
}
.auth-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, #6366f1, #5558e6);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 12px;
}
.auth-header h1 {
  font-size: 20px;
  font-weight: 700;
  color: #1a1b23;
}
.auth-switch {
  text-align: center;
  margin-top: 18px;
  font-size: 13px;
  color: #8e8e9a;
}
.auth-switch a {
  color: #6366f1;
  text-decoration: none;
  font-weight: 600;
}
</style>
```

- [ ] **Step 2: Create RegisterPage**

Create `frontend/src/views/RegisterPage.vue`:

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h1>注册 LLM Chat</h1>
      </div>
      <n-form :model="form" label-placement="top">
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" placeholder="2-50 个字符" size="large" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="至少 4 个字符" size="large" />
        </n-form-item>
        <n-button type="primary" block size="large" :loading="loading" @click="handleRegister">注册</n-button>
      </n-form>
      <div class="auth-switch">
        已有账号？<router-link to="/login">登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const message = useMessage()
const loading = ref(false)

const form = reactive({ username: '', password: '' })

async function handleRegister() {
  if (!form.username || !form.password) {
    message.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.register(form.username, form.password)
    router.push('/chat')
  } catch (e: any) {
    message.error(e.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page { display: flex; align-items: center; justify-content: center; height: 100vh; background: #f5f5f7; }
.auth-card { width: 380px; background: #fff; border-radius: 16px; padding: 36px 32px 28px; box-shadow: 0 2px 16px rgba(0, 0, 0, 0.06); }
.auth-header { text-align: center; margin-bottom: 28px; }
.auth-icon { width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg, #6366f1, #5558e6); display: inline-flex; align-items: center; justify-content: center; color: #fff; margin-bottom: 12px; }
.auth-header h1 { font-size: 20px; font-weight: 700; color: #1a1b23; }
.auth-switch { text-align: center; margin-top: 18px; font-size: 13px; color: #8e8e9a; }
.auth-switch a { color: #6366f1; text-decoration: none; font-weight: 600; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/LoginPage.vue frontend/src/views/RegisterPage.vue
git commit -m "feat: add login and register pages"
```

---

## Phase 5: Frontend Integration

### Task 19: Refactor App.vue for routing and add user menu

**Files:**
- Modify: `frontend/src/App.vue`
- Create: `frontend/src/views/ChatPage.vue`
- Create: `frontend/src/views/BatchPage.vue`
- Create: `frontend/src/views/EsExportPage.vue`

- [ ] **Step 1: Create thin wrapper pages**

The current App.vue contains all the layout. Each view page will be a thin wrapper that imports the existing component directly. However, the existing components (ChatWindow, BatchPanel, EsExportPanel) currently need to be embedded in the layout. The cleanest approach: keep App.vue as the layout shell, and use `<router-view>` inside `<main>`.

Create `frontend/src/views/ChatPage.vue`:

```vue
<template>
  <ChatWindow />
</template>

<script setup lang="ts">
import ChatWindow from '../components/ChatWindow.vue'
</script>
```

Create `frontend/src/views/BatchPage.vue`:

```vue
<template>
  <BatchPanel />
</template>

<script setup lang="ts">
import BatchPanel from '../components/BatchPanel.vue'
</script>
```

Create `frontend/src/views/EsExportPage.vue`:

```vue
<template>
  <EsExportPanel />
</template>

<script setup lang="ts">
import EsExportPanel from '../components/EsExportPanel.vue'
</script>
```

- [ ] **Step 2: Modify App.vue**

Edit `frontend/src/App.vue`. The key changes:
1. Replace `ref('chat')` currentView with route-based active state
2. Replace `<KeepAlive>` with `<router-view>`
3. Add user menu in sidebar footer
4. Import `useRouter`, `useRoute`, `useAuthStore`

Update the `<script setup>`:

```typescript
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NConfigProvider, NMessageProvider, NButton, NDropdown } from 'naive-ui'
import { useChatStore } from './stores/chat'
import { useBatchStore } from './stores/batch'
import { useEsExportStore } from './stores/esExport'
import { useAuthStore } from './stores/auth'
import SessionList from './components/SessionList.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const store = useChatStore()
const batchStore = useBatchStore()
const esExportStore = useEsExportStore()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const currentView = computed(() => route.name as string)

function handleNewChat() {
  if (currentView.value === 'batch') {
    batchStore.newBatchTask()
  } else if (currentView.value === 'es-export') {
    esExportStore.newTask()
  } else {
    store.newConversation()
  }
}

function navigateTo(view: string) {
  router.push(`/${view}`)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}

const userMenuOptions = [
  { label: '修改密码', key: 'password' },
  { label: '退出登录', key: 'logout' },
]

const adminMenuOptions = [
  { label: '用户管理', key: 'users' },
  { label: '修改密码', key: 'password' },
  { label: '退出登录', key: 'logout' },
]

function handleUserSelect(key: string) {
  if (key === 'logout') {
    handleLogout()
  } else if (key === 'password') {
    router.push('/settings/password')
  } else if (key === 'users') {
    router.push('/admin/users')
  }
}
```

Update template — replace the `<main>` area:

```html
<main class="main-area">
  <router-view v-slot="{ Component }">
    <keep-alive>
      <component :is="Component" />
    </keep-alive>
  </router-view>
</main>
```

Replace the nav buttons to use `navigateTo`:

```html
<button :class="['nav-item', { active: currentView === 'chat' }]" @click="navigateTo('chat')">
  ...
</button>
```

Replace the sidebar footer with user menu:

```html
<div class="sidebar-footer">
  <n-dropdown trigger="click" :options="auth.isAdmin ? adminMenuOptions : userMenuOptions" @select="handleUserSelect">
    <div class="footer-user">
      <div class="user-avatar">{{ auth.user?.username?.charAt(0)?.toUpperCase() }}</div>
      <span class="user-name">{{ auth.user?.username }}</span>
      <n-tag v-if="auth.isAdmin" type="info" size="tiny" :bordered="false">管理员</n-tag>
      <svg class="footer-chevron" width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M5 3l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
  </n-dropdown>
</div>
```

In onMounted, add auth store usage — data loading should use the token:

```typescript
onMounted(async () => {
  if (auth.isLoggedIn) {
    await Promise.all([store.loadKeys(), store.loadConversations(), batchStore.loadBatchTasks(), esExportStore.loadTasks()])
  }
})
```

Add styles for the user footer:

```css
.footer-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  color: #b4b4be;
}
.footer-user:hover { background: #252530; }
.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #5558e6);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.user-name {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.vue frontend/src/views/ChatPage.vue frontend/src/views/BatchPage.vue frontend/src/views/EsExportPage.vue
git commit -m "feat: refactor App.vue for routing, add user menu and view pages"
```

---

### Task 20: Update all frontend API files to use authFetch

**Files:**
- Modify: `frontend/src/api/conversations.ts`
- Modify: `frontend/src/api/keys.ts`
- Modify: `frontend/src/api/chat.ts`
- Modify: `frontend/src/api/batch.ts`
- Modify: `frontend/src/api/batchTasks.ts`
- Modify: `frontend/src/api/esExport.ts`

- [ ] **Step 1: Replace fetch with authFetch in all API files**

For each file, replace `fetch(` with `authFetch(` and add the import:

```typescript
import { authFetch } from './client'
```

For `chat.ts` (SSE streaming), use `authFetch` for the initial fetch call:
```typescript
authFetch(`/api/chat/${conversationId}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ content }),
  signal: controller.signal,
})
```

The `auth.ts` file (login/register) should NOT use authFetch — those endpoints are public.

- [ ] **Step 2: Add key override API to keys.ts**

Add to `frontend/src/api/keys.ts`:

```typescript
export async function setKeyOverride(keyId: number, data: { enable_thinking?: boolean | null; max_context_tokens?: number | null }): Promise<void> {
  await authFetch(`${BASE}/${keyId}/overrides`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/conversations.ts frontend/src/api/keys.ts frontend/src/api/chat.ts frontend/src/api/batch.ts frontend/src/api/batchTasks.ts frontend/src/api/esExport.ts
git commit -m "feat: migrate all API calls to authFetch with token injection"
```

---

### Task 21: Create AdminUsersPage

**Files:**
- Create: `frontend/src/views/AdminUsersPage.vue`

- [ ] **Step 1: Write admin users management page**

Create `frontend/src/views/AdminUsersPage.vue`:

```vue
<template>
  <div class="admin-page">
    <div class="admin-header">
      <h2>用户管理</h2>
      <n-button type="primary" @click="showCreate = true">
        <template #icon>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 3v8M3 7h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </template>
        添加用户
      </n-button>
    </div>

    <n-data-table :columns="columns" :data="users" :bordered="false" />

    <!-- Create User Modal -->
    <n-modal v-model:show="showCreate" title="添加用户">
      <n-card style="width: 400px" title="添加用户" :bordered="false" size="small">
        <n-form :model="createForm" label-placement="top">
          <n-form-item label="用户名">
            <n-input v-model:value="createForm.username" placeholder="2-50 个字符" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="createForm.password" type="password" placeholder="至少 4 个字符" />
          </n-form-item>
          <n-form-item label="角色">
            <n-select v-model:value="createForm.role" :options="roleOptions" />
          </n-form-item>
          <n-button type="primary" block :loading="creating" @click="handleCreate">创建</n-button>
        </n-form>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NDataTable, NModal, NCard, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, useMessage } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import * as usersApi from '../api/users'
import type { UserInfo } from '../types'

const message = useMessage()
const users = ref<UserInfo[]>([])
const showCreate = ref(false)
const creating = ref(false)

const createForm = ref({ username: '', password: '', role: 'user' })
const roleOptions = [
  { label: '普通用户', value: 'user' },
  { label: '管理员', value: 'admin' },
]

const columns: DataTableColumns<UserInfo> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '用户名', key: 'username' },
  {
    title: '角色', key: 'role', width: 100,
    render(row) {
      return h(NTag, { type: row.role === 'admin' ? 'info' : 'default', size: 'small', bordered: false }, { default: () => row.role === 'admin' ? '管理员' : '用户' })
    },
  },
  {
    title: '状态', key: 'is_active', width: 80,
    render(row) {
      return h(NTag, { type: row.is_active ? 'success' : 'error', size: 'small', bordered: false }, { default: () => row.is_active ? '正常' : '禁用' })
    },
  },
  { title: '创建时间', key: 'created_at', width: 170 },
  {
    title: '操作', key: 'actions', width: 220,
    render(row) {
      return h('div', { style: 'display:flex;gap:6px;' }, [
        h(NButton, { text: true, size: 'tiny', onClick: () => handleToggleActive(row) }, { default: () => row.is_active ? '禁用' : '启用' }),
        h(NButton, { text: true, size: 'tiny', onClick: () => handleResetPassword(row) }, { default: () => '重置密码' }),
        h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
          trigger: () => h(NButton, { text: true, size: 'tiny', type: 'error' }, { default: () => '删除' }),
          default: () => '确认删除此用户？',
        }),
      ])
    },
  },
]

async function loadUsers() { users.value = await usersApi.fetchUsers() }

async function handleCreate() {
  if (!createForm.value.username || !createForm.value.password) {
    message.warning('请填写用户名和密码')
    return
  }
  creating.value = true
  try {
    await usersApi.createUser(createForm.value)
    message.success('用户已创建')
    showCreate.value = false
    createForm.value = { username: '', password: '', role: 'user' }
    await loadUsers()
  } catch (e: any) {
    message.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleToggleActive(row: UserInfo) {
  await usersApi.updateUser(row.id, { is_active: !row.is_active })
  await loadUsers()
}

async function handleResetPassword(row: UserInfo) {
  try {
    const newPwd = await usersApi.resetUserPassword(row.id)
    message.success(`密码已重置为: ${newPwd}`)
  } catch (e: any) {
    message.error(e.message || '重置失败')
  }
}

async function handleDelete(id: number) {
  await usersApi.deleteUser(id)
  message.success('用户已删除')
  await loadUsers()
}

onMounted(() => loadUsers())
</script>

<style scoped>
.admin-page { padding: 32px; max-width: 900px; margin: 0 auto; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.admin-header h2 { font-size: 20px; font-weight: 700; color: #1a1b23; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/AdminUsersPage.vue
git commit -m "feat: add admin user management page"
```

---

### Task 22: Create ChangePasswordPage

**Files:**
- Create: `frontend/src/views/ChangePasswordPage.vue`

- [ ] **Step 1: Write change password page**

Create `frontend/src/views/ChangePasswordPage.vue`:

```vue
<template>
  <div class="cp-page">
    <div class="cp-card">
      <h2>修改密码</h2>
      <n-form :model="form" label-placement="top">
        <n-form-item label="原密码">
          <n-input v-model:value="form.oldPassword" type="password" show-password-on="click" placeholder="输入原密码" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input v-model:value="form.newPassword" type="password" show-password-on="click" placeholder="至少 4 个字符" />
        </n-form-item>
        <div class="cp-actions">
          <n-button type="primary" :loading="loading" @click="handleSubmit">保存</n-button>
          <n-button @click="$router.push('/chat')">取消</n-button>
        </div>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui'
import { changePassword } from '../api/auth'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const form = reactive({ oldPassword: '', newPassword: '' })

async function handleSubmit() {
  if (!form.oldPassword || !form.newPassword) {
    message.warning('请填写完整')
    return
  }
  loading.value = true
  try {
    await changePassword(form.oldPassword, form.newPassword)
    message.success('密码已修改')
    router.push('/chat')
  } catch (e: any) {
    message.error(e.message || '修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.cp-page { display: flex; align-items: center; justify-content: center; height: 100%; }
.cp-card { width: 380px; background: #fff; border-radius: 16px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,0.05); }
.cp-card h2 { font-size: 18px; font-weight: 700; margin-bottom: 20px; }
.cp-actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ChangePasswordPage.vue
git commit -m "feat: add change password page"
```

---

### Task 23: Modify SettingsPanel for shared/private key distinction + overrides

**Files:**
- Modify: `frontend/src/components/SettingsPanel.vue`

- [ ] **Step 1: Update SettingsPanel**

The key changes:
1. Import `useAuthStore` to check if user is admin
2. In the "已配置的 Key" section, split into "共享 Key" and "我的 Key" groups
3. For shared keys, show an override toggle for `enable_thinking` and `max_context_tokens`
4. Show "共享" badge on shared keys
5. Hide edit/delete for shared keys when not admin
6. Import and use `setKeyOverride` API

Key modifications to `SettingsPanel.vue`:

In the `<script setup>`, add:
```typescript
import { useAuthStore } from '../stores/auth'
import { setKeyOverride } from '../api/keys'

const auth = useAuthStore()

const sharedKeys = computed(() => store.apiKeys.filter(k => k.user_id === null || k.user_id === undefined))
const myKeys = computed(() => store.apiKeys.filter(k => k.user_id !== null && k.user_id !== undefined))
```

In the template, replace the single key list with two sections. For shared keys: hide delete/edit buttons when `!auth.isAdmin`, add override switches. The key card for a shared key (non-admin view) should show:
- Key name + "共享" badge
- enable_thinking toggle (calls setKeyOverride)
- max_context_tokens input (calls setKeyOverride)

For creating keys:
- Admin: can create both shared and private keys (add a toggle / note)
- Regular user: always creates private keys

The form for admin should show a note: "管理员创建的 Key 默认为全员共享"

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/SettingsPanel.vue
git commit -m "feat: add shared/private key distinction with user overrides in settings"
```

---

## Phase 6: Final Integration

### Task 24: End-to-end verification

- [ ] **Step 1: Run all backend tests**

Run: `cd /mnt/d/zhcs/model-web/backend && python -m pytest tests/ -v`

Expected: all tests pass.

- [ ] **Step 2: Build frontend**

Run: `cd /mnt/d/zhcs/model-web/frontend && npx vue-tsc --noEmit 2>&1 | head -30`

Check for type errors. Fix any issues.

Run: `cd /mnt/d/zhcs/model-web/frontend && npm run build`

Expected: build succeeds.

- [ ] **Step 3: Manual smoke test checklist**

Start the server and verify:
1. Visit `/` → redirected to `/login`
2. Register first user → logged in → sees chat
3. First user is admin → sees "管理员" tag in sidebar
4. Admin nav to `/admin/users` → sees user table
5. Admin creates a new user
6. Admin creates a shared API key
7. Logout → login as new user → sees shared key in settings
8. User overrides `enable_thinking` on shared key
9. User creates conversation → data isolated
10. User cannot access `/admin/users`
11. User changes password → can login with new password

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore: final integration fixes and verification"
```
