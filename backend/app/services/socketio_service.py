"""
Socket.IO Service for Real-time Frontend Communication

Provides real-time message push to frontend clients.
"""

import socketio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Create Socket.IO server with ASGI support
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Allow all origins for development
    logger=True,  # Enable logging for debugging
    engineio_logger=True,  # Enable engine.io logging
)

# Track connected clients
connected_clients: set[str] = set()


@sio.on('connect')
async def on_connect(sid: str, environ: dict) -> bool:
    """Handle client connection."""
    connected_clients.add(sid)
    logger.info(f"[SocketIO] Client connected: {sid}, total clients: {len(connected_clients)}")
    print(f"[SocketIO] Client connected: {sid}, total clients: {len(connected_clients)}")
    return True


@sio.on('disconnect')
async def on_disconnect(sid: str) -> None:
    """Handle client disconnection."""
    connected_clients.discard(sid)
    logger.info(f"[SocketIO] Client disconnected: {sid}, total clients: {len(connected_clients)}")
    print(f"[SocketIO] Client disconnected: {sid}, total clients: {len(connected_clients)}")


async def push_message_to_session(session_id: str, message: dict) -> bool:
    """
    Push a message to all clients subscribed to a session.

    Args:
        session_id: The session ID to push to
        message: The message data to push

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        logger.debug(f"[SocketIO] No connected clients, skipping push for session {session_id}")
        return False

    event_data = {
        "type": "message",
        "session_id": session_id,
        "data": message,
    }

    try:
        # Emit to the session-specific room
        await sio.emit('message', event_data, room=f"session:{session_id}")
        logger.info(f"[SocketIO] Pushed message to session {session_id}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push message: {e}")
        return False


async def push_status_update(instance_id: str, status: str) -> bool:
    """
    Push instance status update to all clients.

    Args:
        instance_id: The instance ID
        status: The new status

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        return False

    event_data = {
        "type": "status",
        "instance_id": instance_id,
        "status": status,
    }

    try:
        await sio.emit('status', event_data)
        logger.info(f"[SocketIO] Pushed status update for instance {instance_id}: {status}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push status: {e}")
        return False


async def join_session_room(sid: str, session_id: str) -> None:
    """Join a session-specific room for targeted messages."""
    await sio.enter_room(sid, f"session:{session_id}")
    logger.info(f"[SocketIO] Client {sid} joined room session:{session_id}")


async def leave_session_room(sid: str, session_id: str) -> None:
    """Leave a session-specific room."""
    await sio.leave_room(sid, f"session:{session_id}")
    logger.info(f"[SocketIO] Client {sid} left room session:{session_id}")


# Socket.IO event handlers for room management
@sio.on('join_session')
async def on_join_session(sid: str, session_id: str) -> None:
    """Handle client request to join a session room."""
    await join_session_room(sid, session_id)


@sio.on('leave_session')
async def on_leave_session(sid: str, session_id: str) -> None:
    """Handle client request to leave a session room."""
    await leave_session_room(sid, session_id)


def get_socket_app(app):
    """Wrap a FastAPI app with Socket.IO support."""
    return socketio.ASGIApp(sio, app)