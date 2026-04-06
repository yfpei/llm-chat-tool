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
