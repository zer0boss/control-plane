"""
Pydantic Schemas for API Validation
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Literal, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator, field_serializer

from app.utils.time_utils import beijing_now


# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def format_beijing_datetime(dt: datetime) -> str:
    """Format datetime as Beijing time string with timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 数据库中存储的是北京时间，添加时区信息
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"


# ============================================================================
# Instance Schemas
# ============================================================================

class InstanceStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


class AuthType(str, Enum):
    TOKEN = "token"
    PASSWORD = "password"
    MTLS = "mtls"


class InstanceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=18789, ge=1, le=65535)
    channel_id: str = Field(default="ao", max_length=50)


class InstanceCredentials(BaseModel):
    auth_type: AuthType = AuthType.TOKEN
    token: Optional[str] = Field(default=None, max_length=500)
    password: Optional[str] = Field(default=None, max_length=100)
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    ca_path: Optional[str] = None


class InstanceCreate(InstanceBase):
    credentials: InstanceCredentials

    @field_validator("credentials")
    @classmethod
    def validate_credentials(cls, v: InstanceCredentials) -> InstanceCredentials:
        if v.auth_type == AuthType.TOKEN and not v.token:
            raise ValueError("Token is required when auth_type is 'token'")
        if v.auth_type == AuthType.PASSWORD and not v.password:
            raise ValueError("Password is required when auth_type is 'password'")
        if v.auth_type == AuthType.MTLS and (not v.cert_path or not v.key_path):
            raise ValueError("Certificate and key paths are required when auth_type is 'mtls'")
        return v


class InstanceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    host: Optional[str] = Field(default=None, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    credentials: Optional[InstanceCredentials] = None
    channel_id: Optional[str] = Field(default=None, max_length=50)


class InstanceHealth(BaseModel):
    latency_ms: Optional[float] = None
    last_ping_at: Optional[datetime] = None
    reconnect_count: int = 0
    error_count: int = 0

    @field_serializer('last_ping_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return format_beijing_datetime(dt)


class InstanceResponse(InstanceBase):
    id: str
    status: InstanceStatus
    status_message: Optional[str] = None
    health: InstanceHealth = Field(default_factory=lambda: InstanceHealth())
    last_connected_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('last_connected_at', 'last_error_at', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class InstanceList(BaseModel):
    items: list[InstanceResponse]
    total: int


# ============================================================================
# Session Schemas
# ============================================================================

class SessionCreate(BaseModel):
    instance_id: str
    target: str = Field(..., min_length=1, max_length=255, description="Target session ID")
    context: dict = Field(default_factory=dict)


class SessionResponse(BaseModel):
    id: str
    instance_id: str
    target: str
    context: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    @field_serializer('created_at', 'updated_at', 'last_message_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class SessionList(BaseModel):
    items: list[SessionResponse]
    total: int


# ============================================================================
# Message Schemas
# ============================================================================

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    stream: bool = False
    timeout: int = Field(default=60, ge=1, le=300)


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: MessageRole
    content: str
    metadata: dict = Field(default_factory=dict, alias="extra_data")
    latency_ms: Optional[float] = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True
        populate_by_name = True


class MessageList(BaseModel):
    items: list[MessageResponse]
    total: int


# ============================================================================
# System Schemas
# ============================================================================

class SystemHealth(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    uptime_seconds: float
    instances_connected: int
    instances_total: int
    active_sessions: int


class SystemMetrics(BaseModel):
    messages_total: int
    messages_per_minute: float
    avg_latency_ms: float
    errors_total: int


# ============================================================================
# WebSocket Event Schemas
# ============================================================================

class EventType(str, Enum):
    MESSAGE = "message"
    STATUS = "status"
    ERROR = "error"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


class WebSocketEvent(BaseModel):
    type: EventType
    session_id: Optional[str] = None
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=beijing_now)

    @field_serializer('timestamp')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        return format_beijing_datetime(dt)
