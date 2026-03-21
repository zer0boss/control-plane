"""
Database Models
"""

import uuid
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


class TaskStatus(str, PyEnum):
    """Task status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ASSIGNED = "assigned"
    ANALYZING = "analyzing"
    DECOMPOSED = "decomposed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, PyEnum):
    """Task priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """Task for task management."""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        default=TaskStatus.DRAFT,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority),
        default=TaskPriority.MEDIUM,
    )
    manager_instance_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=beijing_now_naive,
        onupdate=beijing_now_naive,
    )


class SubTaskStatus(str, PyEnum):
    """SubTask status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SubTask(Base):
    """SubTask for task decomposition."""
    __tablename__ = "subtasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[SubTaskStatus] = mapped_column(
        Enum(SubTaskStatus),
        default=SubTaskStatus.PENDING,
    )
    executor_instance_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    order: Mapped[int] = mapped_column(default=0)
    dependencies: Mapped[list] = mapped_column(JSON, default=list)  # list of subtask ids
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=beijing_now_naive,
        onupdate=beijing_now_naive,
    )


class TaskProgressEventType(str, PyEnum):
    """Task progress event type."""
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


class TaskProgress(Base):
    """Task progress events."""
    __tablename__ = "task_progress"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subtask_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    event_type: Mapped[TaskProgressEventType] = mapped_column(
        Enum(TaskProgressEventType),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)


# ============================================================================
# Meeting Models
# ============================================================================

class MeetingStatus(str, PyEnum):
    """Meeting status."""
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MeetingType(str, PyEnum):
    """Meeting type."""
    BRAINSTORM = "brainstorm"
    EXPERT_DISCUSSION = "expert_discussion"
    DECISION_MAKING = "decision_making"
    PROBLEM_SOLVING = "problem_solving"
    REVIEW = "review"


class ParticipantRole(str, PyEnum):
    """Meeting participant role."""
    HOST = "host"
    EXPERT = "expert"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


class Meeting(Base):
    """Meeting for agent collective discussion."""
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    meeting_type: Mapped[MeetingType] = mapped_column(
        Enum(MeetingType),
        default=MeetingType.BRAINSTORM,
    )
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus),
        default=MeetingStatus.DRAFT,
    )
    host_instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    max_rounds: Mapped[int] = mapped_column(default=5)
    current_round: Mapped[int] = mapped_column(default=0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    # 提示词模板
    prompt_template_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # 流程控制
    auto_proceed: Mapped[bool] = mapped_column(default=True)
    current_speaker_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    waiting_for_summary: Mapped[bool] = mapped_column(default=False)
    # 系列会议
    parent_meeting_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    series_order: Mapped[int] = mapped_column(default=1)  # 系列中的顺序，1表示第一次会议
    continue_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 纠偏/深入
    # 时间戳
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=beijing_now_naive,
        onupdate=beijing_now_naive,
    )


class MeetingParticipant(Base):
    """Meeting participant."""
    __tablename__ = "meeting_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole),
        default=ParticipantRole.PARTICIPANT,
    )
    # 关联预定义角色
    role_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "blue_hat", "white_hat"
    role_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "蓝色思考帽"
    role_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "#3B82F6"
    speaking_order: Mapped[int] = mapped_column(default=0)
    expertise: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_spoken_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)


class MeetingMessage(Base):
    """Meeting message."""
    __tablename__ = "meeting_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    instance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    round_number: Mapped[int] = mapped_column(default=1)
    speaking_order: Mapped[int] = mapped_column(default=0)
    message_type: Mapped[str] = mapped_column(String(20), default="statement")
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)


class MeetingRoundStatus(str, PyEnum):
    """Meeting round status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class MeetingRound(Base):
    """Meeting round."""
    __tablename__ = "meeting_rounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    meeting_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(default=1)
    status: Mapped[MeetingRoundStatus] = mapped_column(
        Enum(MeetingRoundStatus),
        default=MeetingRoundStatus.PENDING,
    )
    topic: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 轮次摘要
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summarized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summarized_by_participant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # 时间戳
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)


# ============================================================================
# Meeting Type Role Configuration
# ============================================================================

class MeetingTypeRoleConfig(Base):
    """Role configuration for each meeting type."""
    __tablename__ = "meeting_type_role_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_type: Mapped[MeetingType] = mapped_column(Enum(MeetingType), nullable=False, unique=True)
    roles: Mapped[list] = mapped_column(JSON, default=list)  # [{name, color, description, order}]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=beijing_now_naive,
        onupdate=beijing_now_naive,
    )


# ============================================================================
# Prompt Template Model
# ============================================================================

class PromptTemplate(Base):
    """Prompt template for meeting flow."""
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # 各阶段提示词模板
    opening_template: Mapped[str] = mapped_column(Text, nullable=False)
    round_summary_template: Mapped[str] = mapped_column(Text, nullable=False)
    guided_speak_template: Mapped[str] = mapped_column(Text, nullable=False)
    free_speak_template: Mapped[str] = mapped_column(Text, nullable=False)
    closing_summary_template: Mapped[str] = mapped_column(Text, nullable=False)
    participant_speak_template: Mapped[str] = mapped_column(Text, nullable=False)
    # 参数配置
    max_opening_words: Mapped[int] = mapped_column(default=200)
    max_summary_words: Mapped[int] = mapped_column(default=300)
    max_speak_words: Mapped[int] = mapped_column(default=300)
    # 状态
    is_default: Mapped[bool] = mapped_column(default=False)
    is_system: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=beijing_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=beijing_now_naive,
        onupdate=beijing_now_naive,
    )
