"""
Database Models
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, Float, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.time_utils import beijing_now_naive


class InstanceStatus(str, PyEnum):
    """OpenClaw instance connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


class Instance(Base):
    """OpenClaw instance configuration."""
    __tablename__ = "instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(default=18789)
    auth_type: Mapped[str] = mapped_column(String(20), default="token")  # token, password, mtls
    credentials: Mapped[dict] = mapped_column(JSON, default=dict)
    channel_id: Mapped[str] = mapped_column(String(50), default="ao")
    status: Mapped[InstanceStatus] = mapped_column(
        Enum(InstanceStatus),
        default=InstanceStatus.DISCONNECTED,
    )
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=beijing_now_naive,
        onupdate=beijing_now_naive,
    )
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)


class Session(Base):
    """Chat session with an OpenClaw instance."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)  # sessionId/destination
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=beijing_now_naive,
        onupdate=beijing_now_naive,
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class MessageRole(str, PyEnum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """Chat message."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)


class SystemLog(Base):
    """System logs for auditing."""
    __tablename__ = "system_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # INFO, WARN, ERROR
    component: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
