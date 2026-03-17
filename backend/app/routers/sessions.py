"""
Session and Message API Routes
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.session_manager import SessionService, MessageService
from app.services.instance_manager import InstanceService
from app.connectors.ao_plugin import get_connector_pool
from app.schemas import (
    SessionCreate,
    SessionResponse,
    SessionList,
    MessageSend,
    MessageResponse,
    MessageList,
)
from app.utils.time_utils import beijing_now, format_beijing_time

router = APIRouter(prefix="/sessions", tags=["sessions"])

# 文件日志
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "control-plane-ws.log")

def _log_to_file(message: str):
    """写入日志到文件"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            ts = format_beijing_time(beijing_now())
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


async def get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    """Dependency to get session service."""
    return SessionService(db)


async def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    """Dependency to get message service."""
    return MessageService(db)


async def get_instance_service(db: AsyncSession = Depends(get_db)) -> InstanceService:
    """Dependency to get instance service."""
    return InstanceService(db)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    session_service: SessionService = Depends(get_session_service),
    instance_service: InstanceService = Depends(get_instance_service),
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Create a new chat session."""
    # Verify instance exists
    instance = await instance_service.get_instance(data.instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )

    session = await session_service.create_session(data)
    return session_service.to_response(session)


@router.get("", response_model=SessionList)
async def list_sessions(
    instance_id: str | None = None,
    session_service: SessionService = Depends(get_session_service)
) -> SessionList:
    """List sessions."""
    if instance_id:
        sessions = await session_service.list_instance_sessions(instance_id)
    else:
        # List all sessions across all instances
        sessions = await session_service.list_all_sessions()

    return SessionList(
        items=[session_service.to_response(s) for s in sessions],
        total=len(sessions)
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """Get session details."""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session_service.to_response(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> None:
    """Delete a session."""
    success = await session_service.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )


@router.post("/{session_id}/close")
async def close_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service)
) -> dict:
    """Close a session (mark as inactive)."""
    success = await session_service.close_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return {"success": True, "status": "closed"}


# ============================================================================
# Messages
# ============================================================================

@router.get("/{session_id}/messages", response_model=MessageList)
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    session_service: SessionService = Depends(get_session_service),
    message_service: MessageService = Depends(get_message_service)
) -> MessageList:
    """Get messages for a session."""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    messages = await message_service.get_session_messages(session_id, limit, offset)
    return MessageList(
        items=[message_service.to_response(m) for m in messages],
        total=len(messages)
    )


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    data: MessageSend,
    session_service: SessionService = Depends(get_session_service),
    message_service: MessageService = Depends(get_message_service),
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Send a message in a session."""
    _log_to_file(f"[API] send_message called: session_id={session_id}, content={data.content[:50] if data.content else 'N/A'}...")

    session = await session_service.get_session(session_id)
    if not session:
        _log_to_file(f"[API] Session not found: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if not session.is_active:
        _log_to_file(f"[API] Session not active: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active"
        )

    _log_to_file(f"[API] Session found: instance_id={session.instance_id}")

    # Get instance connector
    connector_pool = get_connector_pool()
    _log_to_file(f"[API] Connector pool has {len(connector_pool.get_all_connectors())} connectors")

    connector = connector_pool.get_connector(session.instance_id)
    if not connector:
        _log_to_file(f"[API] No connector found for instance_id={session.instance_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Instance is not connected"
        )

    if not connector.is_connected:
        _log_to_file(f"[API] Connector not connected: instance_id={session.instance_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Instance is not connected"
        )

    _log_to_file(f"[API] Connector found and connected: ws_url={connector.ws_url}")

    # Send message via AO Plugin
    # Use session_id (UUID) as sessionId, not target
    request_id = await connector.send_message(
        connector.config.channel_id,
        session_id,  # Use UUID session_id for proper message routing
        data.content
    )

    if not request_id:
        _log_to_file(f"[API] Failed to send message: request_id is None")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

    _log_to_file(f"[API] Message sent successfully: request_id={request_id}")

    # Store message
    message = await message_service.create_message(
        session_id=session_id,
        role="user",
        content=data.content,
        metadata={"request_id": request_id}
    )

    # Update session
    await session_service.update_last_message(session_id)

    return message_service.to_response(message)
