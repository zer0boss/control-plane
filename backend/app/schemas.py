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


# ============================================================================
# Task Schemas
# ============================================================================

class TaskStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ASSIGNED = "assigned"
    ANALYZING = "analyzing"
    DECOMPOSED = "decomposed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    tags: list[str] = Field(default_factory=list)
    extra_data: dict = Field(default_factory=dict)
    deadline: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    priority: Optional[TaskPriority] = None
    tags: Optional[list[str]] = None
    extra_data: Optional[dict] = None
    deadline: Optional[datetime] = None
    status: Optional[TaskStatus] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    manager_instance_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    extra_data: dict = Field(default_factory=dict)
    result: Optional[str] = None
    summary: Optional[str] = None
    deadline: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('deadline', 'started_at', 'completed_at', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class TaskList(BaseModel):
    items: list[TaskResponse]
    total: int


class TaskAssignManager(BaseModel):
    manager_instance_id: str


class TaskAnalyze(BaseModel):
    analysis: str = Field(..., description="Task analysis result")
    subtasks: list[dict] = Field(default_factory=list, description="Decomposed subtasks")


class TaskConfirm(BaseModel):
    confirmed: bool = True


# ============================================================================
# SubTask Schemas
# ============================================================================

class SubTaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    order: int = Field(default=0)
    dependencies: list[str] = Field(default_factory=list)


class SubTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[SubTaskStatus] = None
    executor_instance_id: Optional[str] = None
    order: Optional[int] = None
    dependencies: Optional[list[str]] = None
    result: Optional[str] = None
    error_message: Optional[str] = None


class SubTaskResponse(BaseModel):
    id: str
    task_id: str
    title: str
    description: Optional[str] = None
    status: SubTaskStatus
    executor_instance_id: Optional[str] = None
    order: int
    dependencies: list[str] = Field(default_factory=list)
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class SubTaskList(BaseModel):
    items: list[SubTaskResponse]
    total: int


# ============================================================================
# Task Progress Schemas
# ============================================================================

class TaskProgressEventType(str, Enum):
    CREATED = "created"
    PUBLISHED = "published"
    ASSIGNED = "assigned"
    ANALYZING = "analyzing"
    DECOMPOSED = "decomposed"
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SUBTASK_CREATED = "subtask_created"
    SUBTASK_ASSIGNED = "subtask_assigned"
    SUBTASK_STARTED = "subtask_started"
    SUBTASK_COMPLETED = "subtask_completed"
    SUBTASK_FAILED = "subtask_failed"


class TaskProgressResponse(BaseModel):
    id: str
    task_id: str
    subtask_id: Optional[str] = None
    event_type: TaskProgressEventType
    message: Optional[str] = None
    progress_percent: int
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class TaskProgressList(BaseModel):
    items: list[TaskProgressResponse]
    total: int


# ============================================================================
# Meeting Schemas
# ============================================================================

class MeetingStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MeetingType(str, Enum):
    BRAINSTORM = "brainstorm"
    EXPERT_DISCUSSION = "expert_discussion"
    DECISION_MAKING = "decision_making"
    PROBLEM_SOLVING = "problem_solving"
    REVIEW = "review"


class ParticipantRole(str, Enum):
    HOST = "host"
    EXPERT = "expert"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    meeting_type: MeetingType = Field(default=MeetingType.BRAINSTORM)
    host_instance_id: str
    max_rounds: int = Field(default=5, ge=1, le=20)
    context: dict = Field(default_factory=dict)
    prompt_template_id: Optional[str] = None
    auto_proceed: bool = Field(default=True)


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    meeting_type: Optional[MeetingType] = None
    host_instance_id: Optional[str] = None
    max_rounds: Optional[int] = Field(default=None, ge=1, le=20)
    context: Optional[dict] = None
    status: Optional[MeetingStatus] = None
    prompt_template_id: Optional[str] = None
    auto_proceed: Optional[bool] = None


class MeetingResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    meeting_type: MeetingType
    status: MeetingStatus
    host_instance_id: str
    max_rounds: int
    current_round: int
    summary: Optional[str] = None
    context: dict = Field(default_factory=dict)
    prompt_template_id: Optional[str] = None
    auto_proceed: bool = True
    current_speaker_id: Optional[str] = None
    waiting_for_summary: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer('started_at', 'completed_at', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class MeetingList(BaseModel):
    items: list[MeetingResponse]
    total: int


# ============================================================================
# Meeting Participant Schemas
# ============================================================================

class ParticipantCreate(BaseModel):
    instance_id: str
    role: ParticipantRole = Field(default=ParticipantRole.PARTICIPANT)
    speaking_order: int = Field(default=0, ge=0)
    expertise: Optional[str] = Field(default=None, max_length=500)
    # 预定义角色关联
    role_code: Optional[str] = Field(default=None, max_length=50)
    role_name: Optional[str] = Field(default=None, max_length=100)
    role_color: Optional[str] = Field(default=None, max_length=20)


class ParticipantUpdate(BaseModel):
    role: Optional[ParticipantRole] = None
    speaking_order: Optional[int] = Field(default=None, ge=0)
    expertise: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None
    role_code: Optional[str] = Field(default=None, max_length=50)
    role_name: Optional[str] = Field(default=None, max_length=100)
    role_color: Optional[str] = Field(default=None, max_length=20)


class ParticipantResponse(BaseModel):
    id: str
    meeting_id: str
    instance_id: str
    role: ParticipantRole
    speaking_order: int
    expertise: Optional[str] = None
    is_active: bool
    last_spoken_at: Optional[datetime] = None
    created_at: datetime
    # 预定义角色信息
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    role_color: Optional[str] = None

    @field_serializer('last_spoken_at', 'created_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class ParticipantList(BaseModel):
    items: list[ParticipantResponse]
    total: int


class ParticipantsReorder(BaseModel):
    participant_orders: list[dict]  # [{"id": "uuid", "speaking_order": 1}, ...]


# ============================================================================
# Meeting Message Schemas
# ============================================================================

class MeetingMessageResponse(BaseModel):
    id: str
    meeting_id: str
    participant_id: str
    instance_id: str
    content: str
    round_number: int
    speaking_order: int
    message_type: str
    extra_data: dict = Field(default_factory=dict)
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class MeetingMessageList(BaseModel):
    items: list[MeetingMessageResponse]
    total: int


class MeetingMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="statement")


# ============================================================================
# Meeting Round Schemas
# ============================================================================

class MeetingRoundStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class MeetingRoundResponse(BaseModel):
    id: str
    meeting_id: str
    round_number: int
    status: MeetingRoundStatus
    topic: Optional[str] = None
    summary: Optional[str] = None
    summarized_at: Optional[datetime] = None
    summarized_by_participant_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    @field_serializer('summarized_at', 'started_at', 'completed_at', 'created_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class MeetingRoundList(BaseModel):
    items: list[MeetingRoundResponse]
    total: int


class MeetingRoundCreate(BaseModel):
    topic: Optional[str] = Field(default=None, max_length=500)


# ============================================================================
# Meeting Transcript Schema
# ============================================================================

class MeetingTranscript(BaseModel):
    meeting: MeetingResponse
    participants: list[ParticipantResponse]
    messages: list[MeetingMessageResponse]
    rounds: list[MeetingRoundResponse]


# ============================================================================
# Speak Invitation Schema
# ============================================================================

class SpeakInvitation(BaseModel):
    participant_id: str


class NextSpeakerRequest(BaseModel):
    participant_id: str


class DirectMessageRequest(BaseModel):
    """Request schema for sending a direct message from host to a participant."""
    participant_id: str
    content: str = Field(..., min_length=1, max_length=5000)


# ============================================================================
# Prompt Template Schemas
# ============================================================================

class PromptTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    opening_template: str
    round_summary_template: str
    guided_speak_template: str
    free_speak_template: str
    closing_summary_template: str
    participant_speak_template: str
    max_opening_words: int = Field(default=200, ge=50, le=1000)
    max_summary_words: int = Field(default=300, ge=50, le=1000)
    max_speak_words: int = Field(default=300, ge=50, le=1000)


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    opening_template: Optional[str] = None
    round_summary_template: Optional[str] = None
    guided_speak_template: Optional[str] = None
    free_speak_template: Optional[str] = None
    closing_summary_template: Optional[str] = None
    participant_speak_template: Optional[str] = None
    max_opening_words: Optional[int] = Field(default=None, ge=50, le=1000)
    max_summary_words: Optional[int] = Field(default=None, ge=50, le=1000)
    max_speak_words: Optional[int] = Field(default=None, ge=50, le=1000)


class PromptTemplateResponse(BaseModel):
    id: str
    name: str
    code: str
    opening_template: str
    round_summary_template: str
    guided_speak_template: str
    free_speak_template: str
    closing_summary_template: str
    participant_speak_template: str
    max_opening_words: int
    max_summary_words: int
    max_speak_words: int
    is_default: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        return format_beijing_datetime(dt)

    class Config:
        from_attributes = True


class PromptTemplateList(BaseModel):
    items: list[PromptTemplateResponse]
    total: int
