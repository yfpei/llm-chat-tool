from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- API Key Schemas ---
class ApiKeyCreate(BaseModel):
    name: str
    provider: str
    base_url: str
    api_key: str
    model: str
    max_context_tokens: int = 200000
    enable_thinking: bool = True
    is_xinghuo_x1: bool = False


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    max_context_tokens: Optional[int] = None
    enable_thinking: Optional[bool] = None
    is_xinghuo_x1: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    model: str
    max_context_tokens: int
    enable_thinking: bool
    is_xinghuo_x1: bool
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


# --- Batch Schemas ---
class BatchUploadResponse(BaseModel):
    task_id: str
    file_id: str
    filename: str
    columns: list[str]
    headers: list[str]
    total_rows: int
    preview: list[dict]


class BatchRunRequest(BaseModel):
    task_id: str
    file_id: str
    input_columns: list[str]
    output_column_name: str = "AI结果"
    prompt: str
    api_key_id: int
    concurrency: int = 3
    strip_thinking: bool = False
    parse_json: bool = False


# --- Batch Task Schemas ---
class BatchTaskCreate(BaseModel):
    file_id: str
    filename: str
    columns: list[str]
    headers: list[str]
    total_rows: int


class BatchTaskUpdate(BaseModel):
    title: Optional[str] = None
    config_json: Optional[str] = None
    status: Optional[str] = None
    progress_completed: Optional[int] = None
    progress_total: Optional[int] = None


class BatchTaskResponse(BaseModel):
    id: str
    title: str
    file_id: str
    filename: str
    columns: str
    headers: str
    total_rows: int
    status: str
    config_json: Optional[str] = None
    progress_completed: int
    progress_total: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
