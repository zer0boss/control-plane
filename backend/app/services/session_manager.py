"""
Session Management Service

Manages chat sessions with OpenClaw instances.
"""

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Session, Message, MessageRole
from app.schemas import SessionCreate, SessionResponse, MessageSend, MessageResponse, MessageRole as MessageRoleEnum
from app.utils.time_utils import beijing_now_naive


class SessionService:
    """Service for managing chat sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, data: SessionCreate) -> Session:
        """Create a new session."""
        session = Session(
            id=str(uuid.uuid4()),
            instance_id=data.instance_id,
            target=data.target,
            context=data.context,
            is_active=True,
            created_at=beijing_now_naive(),
            updated_at=beijing_now_naive(),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def list_instance_sessions(self, instance_id: str) -> list[Session]:
        """List all sessions for an instance."""
        result = await self.db.execute(
            select(Session)
            .where(Session.instance_id == instance_id)
            .order_by(Session.updated_at.desc())
        )
        return result.scalars().all()

    async def list_all_sessions(self) -> list[Session]:
        """List all sessions across all instances."""
        result = await self.db.execute(
            select(Session)
            .order_by(Session.updated_at.desc())
        )
        return result.scalars().all()

    async def close_session(self, session_id: str) -> bool:
        """Close a session."""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.is_active = False
        session.updated_at = beijing_now_naive()
        await self.db.commit()
        return True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        session = await self.get_session(session_id)
        if not session:
            return False

        # Delete associated messages
        await self.db.execute(
            Message.__table__.delete().where(Message.session_id == session_id)
        )

        await self.db.delete(session)
        await self.db.commit()
        return True

    async def update_last_message(self, session_id: str) -> None:
        """Update last message timestamp."""
        session = await self.get_session(session_id)
        if session:
            session.last_message_at = beijing_now_naive()
            session.updated_at = beijing_now_naive()
            await self.db.commit()

    def to_response(self, session: Session) -> SessionResponse:
        """Convert session model to response schema."""
        return SessionResponse(
            id=session.id,
            instance_id=session.instance_id,
            target=session.target,
            context=session.context,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_message_at=session.last_message_at,
        )


class MessageService:
    """Service for managing messages."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[dict] = None,
        latency_ms: Optional[float] = None
    ) -> Message:
        """Create a new message."""
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            extra_data=metadata or {},
            latency_ms=latency_ms,
            created_at=beijing_now_naive(),
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[Message]:
        """Get messages for a session."""
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_message_count(self, session_id: str) -> int:
        """Get total message count for a session."""
        result = await self.db.execute(
            select(func.count()).where(Message.session_id == session_id)
        )
        return result.scalar()

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message by ID."""
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_all_messages(self, limit: int = 100, offset: int = 0) -> list[Message]:
        """Get all messages across all sessions."""
        result = await self.db.execute(
            select(Message)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_instance_messages(
        self, instance_id: str, limit: int = 100, offset: int = 0
    ) -> list[Message]:
        """Get all messages for an instance (via sessions)."""
        from sqlalchemy import join
        result = await self.db.execute(
            select(Message)
            .join(Session, Message.session_id == Session.id)
            .where(Session.instance_id == instance_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def delete_message(self, message_id: str) -> bool:
        """Delete a message by ID."""
        message = await self.get_message(message_id)
        if not message:
            return False
        await self.db.delete(message)
        await self.db.commit()
        return True

    async def search_messages(
        self, query: str, session_id: Optional[str] = None, limit: int = 50
    ) -> list[Message]:
        """Search messages by content."""
        stmt = select(Message).where(Message.content.ilike(f"%{query}%"))
        if session_id:
            stmt = stmt.where(Message.session_id == session_id)
        stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    def to_response(self, message: Message) -> MessageResponse:
        """Convert message model to response schema."""
        role_map = {
            MessageRole.USER: MessageRoleEnum.USER,
            MessageRole.ASSISTANT: MessageRoleEnum.ASSISTANT,
            MessageRole.SYSTEM: MessageRoleEnum.SYSTEM,
        }
        return MessageResponse(
            id=message.id,
            session_id=message.session_id,
            role=role_map.get(message.role, MessageRoleEnum.SYSTEM),
            content=message.content,
            metadata=message.extra_data,
            latency_ms=message.latency_ms,
            created_at=message.created_at,
        )
