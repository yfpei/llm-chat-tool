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
    active_key_id = Column(Integer, nullable=True)
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
    provider = Column(String(20), nullable=False)  # "openai" or "anthropic"
    base_url = Column(String(500), nullable=False)
    api_key = Column(Text, nullable=False)  # encrypted
    model = Column(String(100), nullable=False)
    max_context_tokens = Column(Integer, default=200000)
    enable_thinking = Column(Boolean, default=True)
    model_type = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=False)
    is_valid = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="api_keys")
    conversations = relationship("Conversation", back_populates="api_key_rel")
    overrides = relationship("UserKeyOverride", back_populates="api_key", cascade="save-update, merge")


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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="es_export_tasks")
