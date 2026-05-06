# LLM Chat Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal LLM Q&A tool with Vue 3 frontend and FastAPI backend, supporting OpenAI and Anthropic protocols with streaming, API key management, and persistent chat history.

**Architecture:** Frontend (Vue 3 + Naive UI) communicates with FastAPI backend via REST + SSE. Backend proxies LLM calls through a unified provider abstraction, stores encrypted API keys and chat history in SQLite. Context management truncates history exceeding configurable token limits.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, aiosqlite, cryptography (Fernet), tiktoken, openai SDK, anthropic SDK, sse-starlette | Vue 3, Vite, TypeScript, Naive UI, Pinia, markdown-it

---

## File Structure

```
model-web/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS, router mounting
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── keys.py          # API key CRUD + verify + activate
│   │   │   ├── conversations.py # Conversation CRUD
│   │   │   └── chat.py          # Chat SSE endpoint
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── key_service.py   # Key encryption, validation, CRUD
│   │   │   ├── chat_service.py  # Context assembly, token truncation
│   │   │   └── llm/
│   │   │       ├── __init__.py
│   │   │       ├── base.py      # LLMProvider ABC
│   │   │       ├── openai.py    # OpenAI streaming adapter
│   │   │       └── anthropic.py # Anthropic streaming adapter
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── crypto.py        # Fernet encrypt/decrypt helpers
│   │       └── token_counter.py # Token counting per provider
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Shared fixtures (test DB, client)
│   │   ├── test_crypto.py
│   │   ├── test_token_counter.py
│   │   ├── test_keys.py
│   │   ├── test_conversations.py
│   │   └── test_chat_service.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── api/
│   │   │   ├── keys.ts
│   │   │   ├── conversations.ts
│   │   │   └── chat.ts
│   │   ├── components/
│   │   │   ├── ChatWindow.vue
│   │   │   ├── MessageBubble.vue
│   │   │   ├── SessionList.vue
│   │   │   ├── InputBox.vue
│   │   │   └── SettingsPanel.vue
│   │   ├── stores/
│   │   │   └── chat.ts
│   │   └── types/
│   │       └── index.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── docs/
```

---

## Task 1: Backend Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/llm/__init__.py`
- Create: `backend/app/utils/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
aiosqlite==0.20.0
pydantic-settings==2.5.2
cryptography==43.0.1
tiktoken==0.7.0
openai==1.51.0
anthropic==0.34.2
sse-starlette==2.1.3
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
```

- [ ] **Step 2: Create .env file**

```env
ENCRYPTION_KEY=
DATABASE_URL=sqlite+aiosqlite:///./llm_chat.db
```

Generate an encryption key and fill it in:

```bash
cd backend
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output as the `ENCRYPTION_KEY` value.

- [ ] **Step 3: Create config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    encryption_key: str
    database_url: str = "sqlite+aiosqlite:///./llm_chat.db"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: Create database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        from app.models import ApiKey, Conversation, Message  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 5: Create models.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(20), nullable=False)  # "openai" or "anthropic"
    base_url = Column(String(500), nullable=False)
    api_key = Column(Text, nullable=False)  # encrypted
    model = Column(String(100), nullable=False)
    max_context_tokens = Column(Integer, default=200000)
    is_active = Column(Boolean, default=False)
    is_valid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="api_key_rel")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), default="新会话")
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    api_key_rel = relationship("ApiKey", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
```

- [ ] **Step 6: Create schemas.py**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- API Key Schemas ---
class ApiKeyCreate(BaseModel):
    name: str
    provider: str  # "openai" or "anthropic"
    base_url: str
    api_key: str
    model: str
    max_context_tokens: int = 200000


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    max_context_tokens: Optional[int] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    model: str
    max_context_tokens: int
    is_active: bool
    is_valid: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyVerifyResponse(BaseModel):
    is_valid: bool
    message: str


# --- Conversation Schemas ---
class ConversationCreate(BaseModel):
    title: Optional[str] = "新会话"
    api_key_id: Optional[int] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    api_key_id: Optional[int] = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    title: str
    api_key_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


# --- Chat Schemas ---
class ChatRequest(BaseModel):
    content: str
```

- [ ] **Step 7: Create main.py with router stubs**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="LLM Chat Tool", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Create empty __init__.py files**

Create empty `__init__.py` in:
- `backend/app/__init__.py`
- `backend/app/routers/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/services/llm/__init__.py`
- `backend/app/utils/__init__.py`
- `backend/tests/__init__.py`

- [ ] **Step 9: Create test conftest.py**

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db():
    async with TestingSessionLocal() as session:
        yield session
```

- [ ] **Step 10: Run health check test to verify scaffolding**

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v -k "health" --tb=short
```

Write a quick test first:

```python
# tests/test_health.py
import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git.exe add backend/
git.exe commit -m "feat: backend project scaffolding with FastAPI, SQLAlchemy, and test setup"
```

---

## Task 2: Crypto Utilities

**Files:**
- Create: `backend/app/utils/crypto.py`
- Create: `backend/tests/test_crypto.py`

- [ ] **Step 1: Write failing tests for crypto**

```python
# tests/test_crypto.py
from app.utils.crypto import encrypt, decrypt


def test_encrypt_decrypt_roundtrip():
    plaintext = "sk-test-key-12345"
    encrypted = encrypt(plaintext)
    assert encrypted != plaintext
    decrypted = decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_produces_different_output():
    plaintext = "sk-test-key-12345"
    encrypted1 = encrypt(plaintext)
    encrypted2 = encrypt(plaintext)
    # Fernet includes timestamp, so outputs differ
    assert encrypted1 != encrypted2


def test_decrypt_invalid_token():
    import pytest
    with pytest.raises(Exception):
        decrypt("not-a-valid-token")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_crypto.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement crypto.py**

```python
from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.encryption_key.encode())


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_crypto.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git.exe add backend/app/utils/crypto.py backend/tests/test_crypto.py
git.exe commit -m "feat: add Fernet encryption utilities for API key storage"
```

---

## Task 3: Token Counter

**Files:**
- Create: `backend/app/utils/token_counter.py`
- Create: `backend/tests/test_token_counter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_token_counter.py
from app.utils.token_counter import count_tokens


def test_count_tokens_openai():
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    count = count_tokens(messages, provider="openai")
    assert count > 0
    assert isinstance(count, int)


def test_count_tokens_anthropic():
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]
    count = count_tokens(messages, provider="anthropic")
    assert count > 0
    assert isinstance(count, int)


def test_count_tokens_empty():
    count = count_tokens([], provider="openai")
    assert count == 0


def test_count_tokens_multiple_messages():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    count = count_tokens(messages, provider="openai")
    single = count_tokens([messages[0]], provider="openai")
    assert count > single
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_token_counter.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement token_counter.py**

```python
import tiktoken


def count_tokens(messages: list[dict], provider: str) -> int:
    """Count tokens for a list of messages. Uses tiktoken for both providers."""
    if not messages:
        return 0

    # Use cl100k_base encoding (works for GPT-4, Claude approximation)
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    total = 0
    for msg in messages:
        # Each message has overhead tokens (role, formatting)
        total += 4  # approximate overhead per message
        total += len(encoding.encode(msg.get("content", "")))
        total += len(encoding.encode(msg.get("role", "")))
    total += 2  # conversation overhead
    return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_token_counter.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git.exe add backend/app/utils/token_counter.py backend/tests/test_token_counter.py
git.exe commit -m "feat: add token counting utility using tiktoken"
```

---

## Task 4: API Key Management (Service + Router)

**Files:**
- Create: `backend/app/services/key_service.py`
- Create: `backend/app/routers/keys.py`
- Create: `backend/tests/test_keys.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Write failing tests for key CRUD and validation**

```python
# tests/test_keys.py
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
    # Create two keys
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_keys.py -v`
Expected: FAIL

- [ ] **Step 3: Implement key_service.py**

```python
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
```

- [ ] **Step 4: Implement keys router**

```python
# app/routers/keys.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyVerifyResponse
from app.services import key_service

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.post("", response_model=ApiKeyResponse)
async def create_key(data: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    key = await key_service.create_key(db, data)
    return key


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(db: AsyncSession = Depends(get_db)):
    return await key_service.list_keys(db)


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_key(key_id: int, data: ApiKeyUpdate, db: AsyncSession = Depends(get_db)):
    key = await key_service.update_key(db, key_id, data)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return key


@router.delete("/{key_id}")
async def delete_key(key_id: int, db: AsyncSession = Depends(get_db)):
    success = await key_service.delete_key(db, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "deleted"}


@router.post("/{key_id}/verify", response_model=ApiKeyVerifyResponse)
async def verify_key(key_id: int, db: AsyncSession = Depends(get_db)):
    is_valid, message = await key_service.verify_key(db, key_id)
    return ApiKeyVerifyResponse(is_valid=is_valid, message=message)


@router.post("/{key_id}/activate", response_model=ApiKeyResponse)
async def activate_key(key_id: int, db: AsyncSession = Depends(get_db)):
    key = await key_service.activate_key(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return key
```

- [ ] **Step 5: Register keys router in main.py**

Add to `backend/app/main.py` after the CORS middleware:

```python
from app.routers import keys

app.include_router(keys.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_keys.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git.exe add backend/app/services/key_service.py backend/app/routers/keys.py backend/tests/test_keys.py backend/app/main.py
git.exe commit -m "feat: add API key management with CRUD, encryption, validation, and activation"
```

---

## Task 5: Conversation Management (Service + Router)

**Files:**
- Create: `backend/app/routers/conversations.py`
- Create: `backend/tests/test_conversations.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_conversations.py
import pytest


@pytest.mark.asyncio
async def test_create_conversation(client):
    resp = await client.post("/api/conversations", json={"title": "Test Chat"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Chat"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_conversation_default_title(client):
    resp = await client.post("/api/conversations", json={})
    assert resp.status_code == 200
    assert resp.json()["title"] == "新会话"


@pytest.mark.asyncio
async def test_list_conversations(client):
    await client.post("/api/conversations", json={"title": "Chat 1"})
    await client.post("/api/conversations", json={"title": "Chat 2"})
    resp = await client.get("/api/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_conversation_detail(client):
    create_resp = await client.post("/api/conversations", json={"title": "Detail Test"})
    conv_id = create_resp.json()["id"]
    resp = await client.get(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Detail Test"
    assert "messages" in data


@pytest.mark.asyncio
async def test_delete_conversation(client):
    create_resp = await client.post("/api/conversations", json={"title": "To Delete"})
    conv_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/conversations/{conv_id}")
    assert resp.status_code == 200
    list_resp = await client.get("/api/conversations")
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_update_conversation(client):
    create_resp = await client.post("/api/conversations", json={"title": "Old"})
    conv_id = create_resp.json()["id"]
    resp = await client.put(f"/api/conversations/{conv_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_conversations.py -v`
Expected: FAIL (404, router not found)

- [ ] **Step 3: Implement conversations router**

```python
# app/routers/conversations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Conversation
from app.schemas import (
    ConversationCreate, ConversationUpdate,
    ConversationResponse, ConversationDetailResponse,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = Conversation(title=data.title, api_key_id=data.api_key_id)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{conv_id}", response_model=ConversationDetailResponse)
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conv_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.put("/{conv_id}", response_model=ConversationResponse)
async def update_conversation(conv_id: str, data: ConversationUpdate, db: AsyncSession = Depends(get_db)):
    conv = await db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conv, field, value)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    conv = await db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    return {"message": "deleted"}
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import keys, conversations

app.include_router(keys.router)
app.include_router(conversations.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_conversations.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git.exe add backend/app/routers/conversations.py backend/tests/test_conversations.py backend/app/main.py
git.exe commit -m "feat: add conversation CRUD endpoints"
```

---

## Task 6: LLM Provider Layer

**Files:**
- Create: `backend/app/services/llm/base.py`
- Create: `backend/app/services/llm/openai.py`
- Create: `backend/app/services/llm/anthropic.py`

- [ ] **Step 1: Implement LLMProvider base class**

```python
# app/services/llm/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMProvider(ABC):
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Yield content chunks from the LLM response."""
        ...
```

- [ ] **Step 2: Implement OpenAI provider**

```python
# app/services/llm/openai.py
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.services.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        super().__init__(base_url, api_key, model)
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

- [ ] **Step 3: Implement Anthropic provider**

```python
# app/services/llm/anthropic.py
from typing import AsyncGenerator

import anthropic

from app.services.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        super().__init__(base_url, api_key, model)
        self.client = anthropic.AsyncAnthropic(base_url=base_url, api_key=api_key)

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        # Anthropic requires separating system message
        system_content = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }
        if system_content:
            kwargs["system"] = system_content

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
```

- [ ] **Step 4: Add factory function to llm/__init__.py**

```python
# app/services/llm/__init__.py
from app.services.llm.base import LLMProvider
from app.services.llm.openai import OpenAIProvider
from app.services.llm.anthropic import AnthropicProvider


def create_provider(provider: str, base_url: str, api_key: str, model: str) -> LLMProvider:
    if provider == "openai":
        return OpenAIProvider(base_url=base_url, api_key=api_key, model=model)
    elif provider == "anthropic":
        return AnthropicProvider(base_url=base_url, api_key=api_key, model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

- [ ] **Step 5: Commit**

```bash
git.exe add backend/app/services/llm/
git.exe commit -m "feat: add OpenAI and Anthropic LLM provider adapters with streaming"
```

---

## Task 7: Chat Service (Context Management + SSE Endpoint)

**Files:**
- Create: `backend/app/services/chat_service.py`
- Create: `backend/app/routers/chat.py`
- Create: `backend/tests/test_chat_service.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Write failing tests for context truncation**

```python
# tests/test_chat_service.py
import pytest
from app.services.chat_service import truncate_messages


def test_truncate_no_change_when_under_limit():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    result = truncate_messages(messages, max_tokens=200000, provider="openai")
    assert len(result) == 2


def test_truncate_removes_oldest_first():
    # Create many messages that exceed the limit
    messages = [
        {"role": "user", "content": "x " * 5000}  # ~5000 tokens each
        for _ in range(100)
    ]
    result = truncate_messages(messages, max_tokens=10000, provider="openai")
    assert len(result) < len(messages)
    # Last message should always be preserved
    assert result[-1] == messages[-1]


def test_truncate_preserves_system_message():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "x " * 5000},
        {"role": "assistant", "content": "y " * 5000},
        {"role": "user", "content": "z " * 5000},
    ]
    result = truncate_messages(messages, max_tokens=10000, provider="openai")
    # System message should always be present
    assert result[0]["role"] == "system"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_chat_service.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement chat_service.py**

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, Message, ApiKey
from app.services.llm import create_provider
from app.services.key_service import get_decrypted_key
from app.utils.token_counter import count_tokens


def truncate_messages(messages: list[dict], max_tokens: int, provider: str) -> list[dict]:
    """Remove oldest non-system messages until total tokens <= max_tokens."""
    total = count_tokens(messages, provider)
    if total <= max_tokens:
        return messages

    # Separate system messages and chat messages
    system_msgs = [m for m in messages if m["role"] == "system"]
    chat_msgs = [m for m in messages if m["role"] != "system"]

    # Remove from the front of chat_msgs until under limit
    while chat_msgs and count_tokens(system_msgs + chat_msgs, provider) > max_tokens:
        chat_msgs.pop(0)

    return system_msgs + chat_msgs


async def get_conversation_with_key(db: AsyncSession, conversation_id: str):
    """Load conversation with messages and associated API key."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return None, None

    api_key = None
    if conv.api_key_id:
        api_key = await db.get(ApiKey, conv.api_key_id)
    else:
        # Use the active key
        result = await db.execute(select(ApiKey).where(ApiKey.is_active == True))
        api_key = result.scalar_one_or_none()

    return conv, api_key


async def send_message(db: AsyncSession, conversation_id: str, user_content: str):
    """Save user message, build context, stream LLM response, save assistant message."""
    conv, api_key = await get_conversation_with_key(db, conversation_id)
    if not conv:
        raise ValueError("会话不存在")
    if not api_key:
        raise ValueError("未配置 API Key，请先添加并激活一个 API Key")

    # Save user message
    user_msg = Message(conversation_id=conversation_id, role="user", content=user_content)
    db.add(user_msg)
    await db.commit()

    # Build message list from history
    messages = [{"role": m.role, "content": m.content} for m in conv.messages]
    messages.append({"role": "user", "content": user_content})

    # Truncate if needed
    messages = truncate_messages(messages, api_key.max_context_tokens, api_key.provider)

    # Create provider and stream
    plaintext_key = get_decrypted_key(api_key)
    provider = create_provider(api_key.provider, api_key.base_url, plaintext_key, api_key.model)

    full_response = ""

    async def stream():
        nonlocal full_response
        async for chunk in provider.chat_stream(messages):
            full_response += chunk
            yield chunk

    return stream(), conv, lambda: _save_assistant_message(db, conversation_id, conv)


async def _save_assistant_message(db: AsyncSession, conversation_id: str, conv: Conversation):
    """This is called after streaming completes. full_response is captured in the closure."""
    pass  # The actual save happens in the chat router after streaming
```

- [ ] **Step 4: Run tests to verify truncation tests pass**

Run: `cd backend && pytest tests/test_chat_service.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Implement chat router with SSE**

```python
# app/routers/chat.py
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models import Message, Conversation
from app.schemas import ChatRequest
from app.services.chat_service import get_conversation_with_key, truncate_messages
from app.services.llm import create_provider
from app.services.key_service import get_decrypted_key

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{conversation_id}")
async def chat(conversation_id: str, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    conv, api_key = await get_conversation_with_key(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 API Key，请先添加并激活一个 API Key")

    # Save user message
    user_msg = Message(conversation_id=conversation_id, role="user", content=req.content)
    db.add(user_msg)
    conv.updated_at = datetime.utcnow()
    await db.commit()

    # Build context
    await db.refresh(conv, ["messages"])
    messages = [{"role": m.role, "content": m.content} for m in conv.messages]
    messages = truncate_messages(messages, api_key.max_context_tokens, api_key.provider)

    # Create provider
    plaintext_key = get_decrypted_key(api_key)
    provider = create_provider(api_key.provider, api_key.base_url, plaintext_key, api_key.model)

    async def event_generator():
        full_response = ""
        try:
            async for chunk in provider.chat_stream(messages):
                full_response += chunk
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "chunk", "content": chunk}),
                }

            # Save assistant message after streaming completes
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.utcnow()

            # Auto-generate title from first exchange
            if conv.title == "新会话" and full_response:
                conv.title = req.content[:50]

            await db.commit()

            yield {
                "event": "message",
                "data": json.dumps({"type": "done", "content": ""}),
            }
        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "content": str(e)}),
            }

    return EventSourceResponse(event_generator())
```

- [ ] **Step 6: Register chat router in main.py**

Update `backend/app/main.py`:

```python
from app.routers import keys, conversations, chat

app.include_router(keys.router)
app.include_router(conversations.router)
app.include_router(chat.router)
```

- [ ] **Step 7: Run all backend tests**

Run: `cd backend && pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git.exe add backend/app/services/chat_service.py backend/app/routers/chat.py backend/tests/test_chat_service.py backend/app/main.py
git.exe commit -m "feat: add chat endpoint with SSE streaming and context truncation"
```

---

## Task 8: Frontend Project Scaffolding

**Files:**
- Create: `frontend/` (via Vite scaffold)
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: Scaffold Vue 3 + TypeScript project**

```bash
cd /mnt/d/zhcs/model-web
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install
npm install naive-ui pinia markdown-it @types/markdown-it
```

- [ ] **Step 2: Configure Vite proxy**

Replace `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8099',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create TypeScript type definitions**

```typescript
// src/types/index.ts
export interface ApiKeyConfig {
  id: number
  name: string
  provider: 'openai' | 'anthropic'
  base_url: string
  model: string
  max_context_tokens: number
  is_active: boolean
  is_valid: boolean
  created_at: string
}

export interface ApiKeyCreateRequest {
  name: string
  provider: 'openai' | 'anthropic'
  base_url: string
  api_key: string
  model: string
  max_context_tokens: number
}

export interface Conversation {
  id: string
  title: string
  api_key_id: number | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface ChatEvent {
  type: 'chunk' | 'done' | 'error'
  content: string
}
```

- [ ] **Step 4: Verify frontend dev server starts**

```bash
cd /mnt/d/zhcs/model-web/frontend
npm run dev
```

Open browser, verify Vite default page loads. Stop dev server (Ctrl+C).

- [ ] **Step 5: Commit**

```bash
git.exe add frontend/
git.exe commit -m "feat: scaffold Vue 3 + TypeScript frontend with Vite and Naive UI"
```

---

## Task 9: Frontend API Layer

**Files:**
- Create: `frontend/src/api/keys.ts`
- Create: `frontend/src/api/conversations.ts`
- Create: `frontend/src/api/chat.ts`

- [ ] **Step 1: Create keys API**

```typescript
// src/api/keys.ts
import type { ApiKeyConfig, ApiKeyCreateRequest } from '../types'

const BASE = '/api/keys'

export async function fetchKeys(): Promise<ApiKeyConfig[]> {
  const res = await fetch(BASE)
  return res.json()
}

export async function createKey(data: ApiKeyCreateRequest): Promise<ApiKeyConfig> {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateKey(id: number, data: Partial<ApiKeyCreateRequest>): Promise<ApiKeyConfig> {
  const res = await fetch(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteKey(id: number): Promise<void> {
  await fetch(`${BASE}/${id}`, { method: 'DELETE' })
}

export async function verifyKey(id: number): Promise<{ is_valid: boolean; message: string }> {
  const res = await fetch(`${BASE}/${id}/verify`, { method: 'POST' })
  return res.json()
}

export async function activateKey(id: number): Promise<ApiKeyConfig> {
  const res = await fetch(`${BASE}/${id}/activate`, { method: 'POST' })
  return res.json()
}
```

- [ ] **Step 2: Create conversations API**

```typescript
// src/api/conversations.ts
import type { Conversation, ConversationDetail } from '../types'

const BASE = '/api/conversations'

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await fetch(BASE)
  return res.json()
}

export async function createConversation(title?: string): Promise<Conversation> {
  const res = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  return res.json()
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const res = await fetch(`${BASE}/${id}`)
  return res.json()
}

export async function updateConversation(id: string, data: { title?: string; api_key_id?: number }): Promise<Conversation> {
  const res = await fetch(`${BASE}/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/${id}`, { method: 'DELETE' })
}
```

- [ ] **Step 3: Create chat API with SSE**

```typescript
// src/api/chat.ts
import type { ChatEvent } from '../types'

export function sendMessage(
  conversationId: string,
  content: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController()

  fetch(`/api/chat/${conversationId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json()
        onError(err.detail || '请求失败')
        return
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: ChatEvent = JSON.parse(line.slice(6))
              if (event.type === 'chunk') {
                onChunk(event.content)
              } else if (event.type === 'done') {
                onDone()
              } else if (event.type === 'error') {
                onError(event.content)
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError('连接中断')
      }
    })

  return controller
}
```

- [ ] **Step 4: Commit**

```bash
git.exe add frontend/src/api/ frontend/src/types/
git.exe commit -m "feat: add frontend API layer for keys, conversations, and SSE chat"
```

---

## Task 10: Frontend State Management (Pinia Store)

**Files:**
- Create: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/main.ts`

- [ ] **Step 1: Create Pinia chat store**

```typescript
// src/stores/chat.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ApiKeyConfig, Conversation, ConversationDetail, Message } from '../types'
import * as keysApi from '../api/keys'
import * as convApi from '../api/conversations'
import * as chatApi from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  // State
  const apiKeys = ref<ApiKeyConfig[]>([])
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<ConversationDetail | null>(null)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const showSettings = ref(false)

  let abortController: AbortController | null = null

  // API Key actions
  async function loadKeys() {
    apiKeys.value = await keysApi.fetchKeys()
  }

  async function addKey(data: Parameters<typeof keysApi.createKey>[0]) {
    const key = await keysApi.createKey(data)
    apiKeys.value.unshift(key)
    return key
  }

  async function removeKey(id: number) {
    await keysApi.deleteKey(id)
    apiKeys.value = apiKeys.value.filter((k) => k.id !== id)
  }

  async function setActiveKey(id: number) {
    await keysApi.activateKey(id)
    apiKeys.value.forEach((k) => (k.is_active = k.id === id))
  }

  function activeKey(): ApiKeyConfig | undefined {
    return apiKeys.value.find((k) => k.is_active)
  }

  // Conversation actions
  async function loadConversations() {
    conversations.value = await convApi.fetchConversations()
  }

  async function newConversation() {
    const conv = await convApi.createConversation()
    conversations.value.unshift(conv)
    await selectConversation(conv.id)
  }

  async function selectConversation(id: string) {
    currentConversation.value = await convApi.getConversation(id)
  }

  async function removeConversation(id: string) {
    await convApi.deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (currentConversation.value?.id === id) {
      currentConversation.value = null
    }
  }

  async function renameConversation(id: string, title: string) {
    await convApi.updateConversation(id, { title })
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
    if (currentConversation.value?.id === id) {
      currentConversation.value.title = title
    }
  }

  // Chat actions
  function sendMessage(content: string) {
    if (!currentConversation.value || isStreaming.value) return

    const convId = currentConversation.value.id

    // Add user message to UI
    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    currentConversation.value.messages.push(userMsg)

    // Prepare streaming
    isStreaming.value = true
    streamingContent.value = ''

    // Add placeholder assistant message
    const assistantMsg: Message = {
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    }
    currentConversation.value.messages.push(assistantMsg)

    abortController = chatApi.sendMessage(
      convId,
      content,
      (chunk) => {
        streamingContent.value += chunk
        assistantMsg.content = streamingContent.value
      },
      () => {
        isStreaming.value = false
        streamingContent.value = ''
        // Refresh conversation list to update titles/order
        loadConversations()
      },
      (error) => {
        isStreaming.value = false
        assistantMsg.content = `[错误] ${error}`
      },
    )
  }

  function stopStreaming() {
    if (abortController) {
      abortController.abort()
      abortController = null
      isStreaming.value = false
    }
  }

  return {
    apiKeys, conversations, currentConversation,
    isStreaming, streamingContent, showSettings,
    loadKeys, addKey, removeKey, setActiveKey, activeKey,
    loadConversations, newConversation, selectConversation,
    removeConversation, renameConversation,
    sendMessage, stopStreaming,
  }
})
```

- [ ] **Step 2: Update main.ts to register Pinia**

```typescript
// src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
```

- [ ] **Step 3: Commit**

```bash
git.exe add frontend/src/stores/ frontend/src/main.ts
git.exe commit -m "feat: add Pinia chat store with API key, conversation, and streaming management"
```

---

## Task 11: Frontend UI Components

**Files:**
- Create: `frontend/src/components/SessionList.vue`
- Create: `frontend/src/components/MessageBubble.vue`
- Create: `frontend/src/components/InputBox.vue`
- Create: `frontend/src/components/ChatWindow.vue`
- Create: `frontend/src/components/SettingsPanel.vue`
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Create SessionList.vue**

```vue
<!-- src/components/SessionList.vue -->
<template>
  <div class="session-list">
    <n-button block type="primary" @click="store.newConversation()" style="margin-bottom: 12px">
      + 新会话
    </n-button>
    <div
      v-for="conv in store.conversations"
      :key="conv.id"
      :class="['session-item', { active: store.currentConversation?.id === conv.id }]"
      @click="store.selectConversation(conv.id)"
    >
      <span class="session-title">{{ conv.title }}</span>
      <n-popconfirm @positive-click="store.removeConversation(conv.id)">
        <template #trigger>
          <n-button text size="tiny" class="delete-btn" @click.stop>×</n-button>
        </template>
        确认删除此会话？
      </n-popconfirm>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton, NPopconfirm } from 'naive-ui'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
</script>

<style scoped>
.session-list {
  padding: 12px;
  height: 100%;
  overflow-y: auto;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.session-item.active {
  background: rgba(255, 255, 255, 0.15);
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .delete-btn {
  opacity: 1;
}
</style>
```

- [ ] **Step 2: Create MessageBubble.vue**

```vue
<!-- src/components/MessageBubble.vue -->
<template>
  <div :class="['message-bubble', message.role]">
    <div class="message-role">{{ message.role === 'user' ? '你' : 'AI' }}</div>
    <div class="message-content" v-if="message.role === 'user'">{{ message.content }}</div>
    <div class="message-content" v-else v-html="renderedContent"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '../types'

const props = defineProps<{ message: Message }>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const renderedContent = computed(() => md.render(props.message.content || ''))
</script>

<style scoped>
.message-bubble {
  margin-bottom: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 80%;
}

.message-bubble.user {
  background: #e3f2fd;
  margin-left: auto;
}

.message-bubble.assistant {
  background: #f5f5f5;
  margin-right: auto;
}

.message-role {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}

.message-content {
  line-height: 1.6;
  word-break: break-word;
}

.message-content :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}

.message-content :deep(code) {
  background: #e8e8e8;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
}

.message-content :deep(pre code) {
  background: none;
  padding: 0;
}
</style>
```

- [ ] **Step 3: Create InputBox.vue**

```vue
<!-- src/components/InputBox.vue -->
<template>
  <div class="input-box">
    <n-input
      v-model:value="inputText"
      type="textarea"
      :autosize="{ minRows: 1, maxRows: 5 }"
      placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
      @keydown="handleKeydown"
      :disabled="store.isStreaming"
    />
    <n-button
      type="primary"
      :disabled="!inputText.trim() || store.isStreaming"
      @click="send"
      style="margin-left: 8px; align-self: flex-end"
    >
      {{ store.isStreaming ? '生成中...' : '发送' }}
    </n-button>
    <n-button
      v-if="store.isStreaming"
      @click="store.stopStreaming()"
      style="margin-left: 4px; align-self: flex-end"
    >
      停止
    </n-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NInput, NButton } from 'naive-ui'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
const inputText = ref('')

function send() {
  const text = inputText.value.trim()
  if (!text || store.isStreaming) return
  store.sendMessage(text)
  inputText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<style scoped>
.input-box {
  display: flex;
  align-items: flex-start;
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
}
</style>
```

- [ ] **Step 4: Create ChatWindow.vue**

```vue
<!-- src/components/ChatWindow.vue -->
<template>
  <div class="chat-window">
    <div v-if="!store.currentConversation" class="empty-state">
      <h2>LLM Chat</h2>
      <p>创建新会话或选择已有会话开始聊天</p>
    </div>
    <template v-else>
      <div class="messages" ref="messagesRef">
        <MessageBubble
          v-for="msg in store.currentConversation.messages"
          :key="msg.id"
          :message="msg"
        />
      </div>
      <InputBox />
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '../stores/chat'
import MessageBubble from './MessageBubble.vue'
import InputBox from './InputBox.vue'

const store = useChatStore()
const messagesRef = ref<HTMLElement>()

// Auto-scroll on new messages
watch(
  () => store.currentConversation?.messages.length,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)

// Also scroll during streaming
watch(
  () => store.streamingContent,
  async () => {
    await nextTick()
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
</style>
```

- [ ] **Step 5: Create SettingsPanel.vue**

```vue
<!-- src/components/SettingsPanel.vue -->
<template>
  <n-drawer v-model:show="store.showSettings" :width="500" placement="right">
    <n-drawer-content title="API Key 设置">
      <!-- Add Key Form -->
      <n-card title="添加 API Key" size="small" style="margin-bottom: 16px">
        <n-form ref="formRef" :model="form" label-placement="top">
          <n-form-item label="名称">
            <n-input v-model:value="form.name" placeholder="如：我的 OpenAI" />
          </n-form-item>
          <n-form-item label="协议类型">
            <n-select v-model:value="form.provider" :options="providerOptions" @update:value="onProviderChange" />
          </n-form-item>
          <n-form-item label="Base URL">
            <n-input v-model:value="form.base_url" placeholder="API 地址" />
          </n-form-item>
          <n-form-item label="API Key">
            <n-input v-model:value="form.api_key" type="password" show-password-on="click" placeholder="输入 API Key" />
          </n-form-item>
          <n-form-item label="模型">
            <n-input v-model:value="form.model" placeholder="如 gpt-4o 或 claude-sonnet-4-20250514" />
          </n-form-item>
          <n-form-item label="最大上下文 Token">
            <n-input-number v-model:value="form.max_context_tokens" :min="1000" :step="10000" style="width: 100%" />
          </n-form-item>
          <n-button type="primary" block :loading="saving" @click="handleAdd">
            添加并验证
          </n-button>
        </n-form>
      </n-card>

      <!-- Key List -->
      <n-card title="已配置的 Key" size="small">
        <div v-if="store.apiKeys.length === 0" style="color: #888; text-align: center; padding: 20px">
          暂无配置
        </div>
        <div v-for="key in store.apiKeys" :key="key.id" class="key-item">
          <div class="key-info">
            <div class="key-name">
              {{ key.name }}
              <n-tag :type="key.is_valid ? 'success' : 'error'" size="small">
                {{ key.is_valid ? '已验证' : '未验证' }}
              </n-tag>
              <n-tag v-if="key.is_active" type="info" size="small">当前使用</n-tag>
            </div>
            <div class="key-meta">{{ key.provider }} · {{ key.model }}</div>
          </div>
          <div class="key-actions">
            <n-button text size="small" @click="store.setActiveKey(key.id)" :disabled="key.is_active">
              激活
            </n-button>
            <n-button text size="small" @click="handleVerify(key.id)" :loading="verifyingId === key.id">
              验证
            </n-button>
            <n-popconfirm @positive-click="store.removeKey(key.id)">
              <template #trigger>
                <n-button text size="small" type="error">删除</n-button>
              </template>
              确认删除？
            </n-popconfirm>
          </div>
        </div>
      </n-card>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  NDrawer, NDrawerContent, NCard, NForm, NFormItem,
  NInput, NInputNumber, NSelect, NButton, NTag, NPopconfirm,
  useMessage,
} from 'naive-ui'
import { useChatStore } from '../stores/chat'
import { verifyKey } from '../api/keys'

const store = useChatStore()
const message = useMessage()
const saving = ref(false)
const verifyingId = ref<number | null>(null)

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
]

const defaultUrls: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com',
}

const form = reactive({
  name: '',
  provider: 'openai' as 'openai' | 'anthropic',
  base_url: defaultUrls.openai,
  api_key: '',
  model: '',
  max_context_tokens: 200000,
})

function onProviderChange(val: string) {
  form.base_url = defaultUrls[val] || ''
}

async function handleAdd() {
  if (!form.name || !form.api_key || !form.model) {
    message.warning('请填写名称、API Key 和模型')
    return
  }
  saving.value = true
  try {
    const key = await store.addKey({ ...form })
    if (key.is_valid) {
      message.success('添加成功，验证通过')
    } else {
      message.warning('已添加，但验证未通过，请检查配置')
    }
    // Reset form
    form.name = ''
    form.api_key = ''
    form.model = ''
  } catch (e) {
    message.error('添加失败')
  } finally {
    saving.value = false
  }
}

async function handleVerify(id: number) {
  verifyingId.value = id
  try {
    const result = await verifyKey(id)
    await store.loadKeys()
    if (result.is_valid) {
      message.success(result.message)
    } else {
      message.error(result.message)
    }
  } finally {
    verifyingId.value = null
  }
}
</script>

<style scoped>
.key-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.key-item:last-child {
  border-bottom: none;
}

.key-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.key-meta {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}

.key-actions {
  display: flex;
  gap: 8px;
}
</style>
```

- [ ] **Step 6: Create App.vue (main layout)**

```vue
<!-- src/App.vue -->
<template>
  <n-config-provider>
    <n-message-provider>
      <div class="app-layout">
        <header class="app-header">
          <n-button text @click="store.showSettings = true" style="font-size: 18px">
            设置
          </n-button>
          <span class="current-model" v-if="store.activeKey()">
            当前模型: {{ store.activeKey()!.model }}
          </span>
          <span class="current-model" v-else style="color: #f5a623">
            未配置 API Key
          </span>
        </header>
        <div class="app-body">
          <aside class="sidebar">
            <SessionList />
          </aside>
          <main class="main-content">
            <ChatWindow />
          </main>
        </div>
        <SettingsPanel />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { NConfigProvider, NMessageProvider, NButton } from 'naive-ui'
import { useChatStore } from './stores/chat'
import SessionList from './components/SessionList.vue'
import ChatWindow from './components/ChatWindow.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const store = useChatStore()

onMounted(async () => {
  await Promise.all([store.loadKeys(), store.loadConversations()])
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafafa;
}

.current-model {
  font-size: 13px;
  color: #666;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  border-right: 1px solid #e8e8e8;
  background: #f7f7f7;
  overflow-y: auto;
}

.main-content {
  flex: 1;
  overflow: hidden;
}
</style>
```

- [ ] **Step 7: Verify frontend compiles**

```bash
cd /mnt/d/zhcs/model-web/frontend
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 8: Commit**

```bash
git.exe add frontend/src/
git.exe commit -m "feat: add all frontend UI components - session list, chat window, settings panel"
```

---

## Task 12: Integration Test (End-to-End Smoke Test)

**Files:**
- No new files — manual verification

- [ ] **Step 1: Start backend**

```bash
cd /mnt/d/zhcs/model-web/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8099
```

Verify: `http://localhost:8099/api/health` returns `{"status": "ok"}`

- [ ] **Step 2: Start frontend**

In a new terminal:

```bash
cd /mnt/d/zhcs/model-web/frontend
npm run dev
```

Open `http://localhost:5173` in browser.

- [ ] **Step 3: Verify end-to-end flow**

1. Click "设置" — settings panel opens
2. Add an API key (any provider) — verify loading state appears during validation
3. Activate the key
4. Close settings
5. Click "+ 新会话" — new conversation appears in sidebar
6. Type a message and press Enter — verify streaming response appears
7. Create another conversation — verify switching between conversations works

- [ ] **Step 4: Run all backend tests**

```bash
cd /mnt/d/zhcs/model-web/backend
pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 5: Final commit**

```bash
git.exe add -A
git.exe commit -m "feat: complete LLM chat tool with API key management, streaming chat, and Vue 3 frontend"
```
