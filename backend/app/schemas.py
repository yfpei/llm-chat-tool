from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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


# --- API Key Schemas ---
class ApiKeyCreate(BaseModel):
    name: str
    provider: str
    base_url: str
    api_key: str
    model: str
    max_context_tokens: int = 200000
    enable_thinking: bool = True
    model_type: Optional[str] = None


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    max_context_tokens: Optional[int] = None
    enable_thinking: Optional[bool] = None
    model_type: Optional[str] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    model: str
    max_context_tokens: int
    enable_thinking: bool
    model_type: Optional[str] = None
    is_active: bool
    is_valid: bool
    user_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyVerifyResponse(BaseModel):
    is_valid: bool
    message: str


# --- Key Override Schemas ---
class KeyOverrideRequest(BaseModel):
    enable_thinking: bool | None = None
    max_context_tokens: int | None = None


class KeyWithOverridesResponse(ApiKeyResponse):
    owner_username: str | None = None
    user_enable_thinking: bool | None = None
    user_max_context_tokens: int | None = None


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
class FilterCondition(BaseModel):
    field: str
    operator: str  # "contains" | "equals" | "gt" | "lt"
    value: str


class FilterGroup(BaseModel):
    logic: str = "and"  # how conditions within this group combine
    conditions: list[FilterCondition] = []


class FilterConfig(BaseModel):
    top_n: int | None = None
    groups: list[FilterGroup] = []
    logic: str = "and"  # how groups combine



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
    filter: FilterConfig | None = None


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
    eval_config_json: Optional[str] = None
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


# --- ES Export Schemas ---
class EsExportTaskCreate(BaseModel):
    title: str = "未命名导出任务"
    es_host: str
    es_username: Optional[str] = None
    es_password: Optional[str] = None


class EsExportTaskUpdate(BaseModel):
    title: Optional[str] = None
    es_host: Optional[str] = None
    es_username: Optional[str] = None
    es_password: Optional[str] = None
    index_name: Optional[str] = None
    query_dsl: Optional[str] = None
    output_fields: Optional[str] = None
    config_json: Optional[str] = None


class EsExportTaskResponse(BaseModel):
    id: str
    title: str
    es_host: str
    es_username: Optional[str] = None
    index_name: Optional[str] = None
    query_dsl: Optional[str] = None
    output_fields: Optional[str] = None
    status: str
    total_hits: int
    exported_count: int
    file_id: Optional[str] = None
    config_json: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class EsPreviewRequest(BaseModel):
    query_dsl: Optional[dict] = None
    output_fields: Optional[list[str]] = None
    page: int = 1
    page_size: int = 50
    top_n: Optional[int] = None


class EsExportRequest(BaseModel):
    query_dsl: Optional[dict] = None
    output_fields: Optional[list[str]] = None
    top_n: Optional[int] = None


# --- Eval Schemas ---

class MappingRule(BaseModel):
    model_output: str
    label_value: str


class ClassificationEvalConfig(BaseModel):
    label_column: str
    predict_column: str
    mappings: list[MappingRule] = []


class LLMScoringEvalConfig(BaseModel):
    api_key_id: int
    prompt: str
    input_columns: list[str] = []
    score_column: str
    output_column_name: str = "评分"
    concurrency: int = 3


class EvalConfig(BaseModel):
    enabled: bool = False
    method: str = "classification"  # "classification" | "llm_scoring" | "both"

    classification: ClassificationEvalConfig | None = None
    llm_scoring: LLMScoringEvalConfig | None = None


class ClassificationEvalRequest(BaseModel):
    task_id: str
    config: ClassificationEvalConfig


class LLMScoringEvalRequest(BaseModel):
    task_id: str
    config: LLMScoringEvalConfig


class PerClassMetric(BaseModel):
    class_name: str
    precision: float
    recall: float
    f1: float


class AvgMetric(BaseModel):
    precision: float
    recall: float
    f1: float


class ClassificationEvalResponse(BaseModel):
    accuracy: float
    total_samples: int
    num_classes: int
    confusion_matrix: list[list[int]]
    labels: list[str]
    per_class: list[PerClassMetric]
    micro_avg: AvgMetric
    macro_avg: AvgMetric
    skipped_count: int = 0
