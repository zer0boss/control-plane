"""
Messages API Routes

Global message operations across all sessions.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.session_manager import MessageService
from app.schemas import MessageResponse, MessageList

router = APIRouter(prefix="/messages", tags=["messages"])


async def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    """Dependency to get message service."""
    return MessageService(db)


@router.get("", response_model=MessageList)
async def list_messages(
    session_id: Optional[str] = None,
    instance_id: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: MessageService = Depends(get_message_service)
) -> MessageList:
    """
    List messages with optional filtering.

    Args:
        session_id: Filter by specific session
        instance_id: Filter by instance (requires session lookup)
        role: Filter by role (user/assistant/system)
        limit: Maximum number of messages to return
        offset: Pagination offset

    Returns:
        List of messages matching the filters.
    """
    if session_id:
        messages = await service.get_session_messages(session_id, limit, offset)
    elif instance_id:
        # Get all messages for all sessions of an instance
        messages = await service.get_instance_messages(instance_id, limit, offset)
    else:
        # Get all messages globally
        messages = await service.get_all_messages(limit, offset)

    if role:
        messages = [m for m in messages if m.role == role]

    return MessageList(
        items=[service.to_response(m) for m in messages],
        total=len(messages)
    )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    service: MessageService = Depends(get_message_service)
) -> MessageResponse:
    """
    Get a specific message by ID.

    Args:
        message_id: The unique message ID

    Returns:
        Message details.
    """
    message = await service.get_message(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    return service.to_response(message)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    service: MessageService = Depends(get_message_service)
) -> None:
    """
    Delete a message by ID.

    Args:
        message_id: The unique message ID to delete
    """
    success = await service.delete_message(message_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )


@router.get("/search/{query}", response_model=MessageList)
async def search_messages(
    query: str,
    session_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: MessageService = Depends(get_message_service)
) -> MessageList:
    """
    Search messages by content.

    Args:
        query: Search query string
        session_id: Optional session to limit search scope
        limit: Maximum results to return

    Returns:
        Messages containing the search query.
    """
    messages = await service.search_messages(query, session_id, limit)
    return MessageList(
        items=[service.to_response(m) for m in messages],
        total=len(messages)
    )
