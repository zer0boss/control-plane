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


# ============================================================================
# Task Room Management
# ============================================================================

async def join_task_room(sid: str, task_id: str) -> None:
    """Join a task-specific room for targeted messages."""
    await sio.enter_room(sid, f"task:{task_id}")
    logger.info(f"[SocketIO] Client {sid} joined room task:{task_id}")


async def leave_task_room(sid: str, task_id: str) -> None:
    """Leave a task-specific room."""
    await sio.leave_room(sid, f"task:{task_id}")
    logger.info(f"[SocketIO] Client {sid} left room task:{task_id}")


# ============================================================================
# Task Update Push
# ============================================================================

async def push_task_update(task_id: str, event_type: str, data: dict) -> bool:
    """
    Push a task update to all clients subscribed to a task.

    Args:
        task_id: The task ID to push to
        event_type: The event type (e.g., 'created', 'status_changed', 'completed')
        data: The data to push

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        logger.debug(f"[SocketIO] No connected clients, skipping push for task {task_id}")
        return False

    event_data = {
        "type": event_type,
        "task_id": task_id,
        "data": data,
    }

    try:
        await sio.emit('task_update', event_data, room=f"task:{task_id}")
        logger.info(f"[SocketIO] Pushed task update to task {task_id}: {event_type}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push task update: {e}")
        return False


async def push_subtask_update(
    task_id: str,
    subtask_id: str,
    event_type: str,
    data: dict
) -> bool:
    """
    Push a subtask update to all clients subscribed to a task.

    Args:
        task_id: The parent task ID
        subtask_id: The subtask ID
        event_type: The event type
        data: The data to push

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        return False

    event_data = {
        "type": event_type,
        "task_id": task_id,
        "subtask_id": subtask_id,
        "data": data,
    }

    try:
        await sio.emit('subtask_update', event_data, room=f"task:{task_id}")
        logger.info(f"[SocketIO] Pushed subtask update for {subtask_id}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push subtask update: {e}")
        return False


async def push_progress_update(
    task_id: str,
    progress_percent: int,
    message: str = None
) -> bool:
    """
    Push a progress update to all clients subscribed to a task.

    Args:
        task_id: The task ID
        progress_percent: Progress percentage (0-100)
        message: Optional progress message

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        return False

    event_data = {
        "task_id": task_id,
        "progress_percent": progress_percent,
        "message": message,
    }

    try:
        await sio.emit('progress_update', event_data, room=f"task:{task_id}")
        logger.info(f"[SocketIO] Pushed progress update for task {task_id}: {progress_percent}%")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push progress update: {e}")
        return False


# ============================================================================
# Socket.IO Event Handlers for Task Rooms
# ============================================================================

@sio.on('join_task')
async def on_join_task(sid: str, task_id: str) -> None:
    """Handle client request to join a task room."""
    await join_task_room(sid, task_id)


@sio.on('leave_task')
async def on_leave_task(sid: str, task_id: str) -> None:
    """Handle client request to leave a task room."""
    await leave_task_room(sid, task_id)


# ============================================================================
# Meeting Room Management
# ============================================================================

async def join_meeting_room(sid: str, meeting_id: str) -> None:
    """Join a meeting-specific room for targeted messages."""
    await sio.enter_room(sid, f"meeting:{meeting_id}")
    logger.info(f"[SocketIO] Client {sid} joined room meeting:{meeting_id}")


async def leave_meeting_room(sid: str, meeting_id: str) -> None:
    """Leave a meeting-specific room."""
    await sio.leave_room(sid, f"meeting:{meeting_id}")
    logger.info(f"[SocketIO] Client {sid} left room meeting:{meeting_id}")


@sio.on('join_meeting')
async def on_join_meeting(sid: str, meeting_id: str) -> None:
    """Handle client request to join a meeting room."""
    await join_meeting_room(sid, meeting_id)


@sio.on('leave_meeting')
async def on_leave_meeting(sid: str, meeting_id: str) -> None:
    """Handle client request to leave a meeting room."""
    await leave_meeting_room(sid, meeting_id)


# ============================================================================
# Meeting Update Push
# ============================================================================

async def push_meeting_update(meeting_id: str, event_type: str, data: dict) -> bool:
    """
    Push a meeting update to all clients subscribed to a meeting.

    Args:
        meeting_id: The meeting ID to push to
        event_type: The event type (e.g., 'started', 'paused', 'new_round', 'speaker_invited')
        data: The data to push

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        logger.debug(f"[SocketIO] No connected clients, skipping push for meeting {meeting_id}")
        return False

    event_data = {
        "type": event_type,
        "meeting_id": meeting_id,
        "data": data,
    }

    try:
        await sio.emit('meeting_update', event_data, room=f"meeting:{meeting_id}")
        logger.info(f"[SocketIO] Pushed meeting update to meeting {meeting_id}: {event_type}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push meeting update: {e}")
        return False


async def push_meeting_message(meeting_id: str, message: dict) -> bool:
    """
    Push a meeting message to all clients subscribed to a meeting.

    Args:
        meeting_id: The meeting ID to push to
        message: The message data to push

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        logger.debug(f"[SocketIO] No connected clients, skipping push for meeting {meeting_id}")
        return False

    event_data = {
        "meeting_id": meeting_id,
        "message": message,
    }

    try:
        await sio.emit('meeting_message', event_data, room=f"meeting:{meeting_id}")
        logger.info(f"[SocketIO] Pushed meeting message to meeting {meeting_id}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push meeting message: {e}")
        return False


async def push_participant_update(
    meeting_id: str,
    participant_id: str,
    event_type: str,
    data: dict
) -> bool:
    """
    Push a participant update to all clients subscribed to a meeting.

    Args:
        meeting_id: The meeting ID
        participant_id: The participant ID
        event_type: The event type
        data: The data to push

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        return False

    event_data = {
        "type": event_type,
        "meeting_id": meeting_id,
        "participant_id": participant_id,
        "data": data,
    }

    try:
        await sio.emit('participant_update', event_data, room=f"meeting:{meeting_id}")
        logger.info(f"[SocketIO] Pushed participant update for {participant_id}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push participant update: {e}")
        return False


async def push_round_update(
    meeting_id: str,
    round_number: int,
    event_type: str,
    data: dict
) -> bool:
    """
    Push a round update to all clients subscribed to a meeting.

    Args:
        meeting_id: The meeting ID
        round_number: The round number
        event_type: The event type
        data: The data to push

    Returns:
        True if message was sent to at least one client
    """
    if not connected_clients:
        return False

    event_data = {
        "type": event_type,
        "meeting_id": meeting_id,
        "round_number": round_number,
        "data": data,
    }

    try:
        await sio.emit('round_update', event_data, room=f"meeting:{meeting_id}")
        logger.info(f"[SocketIO] Pushed round update for round {round_number}")
        return True
    except Exception as e:
        logger.error(f"[SocketIO] Failed to push round update: {e}")
        return False