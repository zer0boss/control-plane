"""
System API Routes

System health, configuration, and management endpoints.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import get_settings
from app.services.metrics_collector import get_metrics_collector
from app.connectors.ao_plugin import get_connector_pool
from app.schemas import SystemHealth, SystemMetrics

router = APIRouter(prefix="/system", tags=["system"])

# Track startup time
_start_time = time.time()


@router.get("/health", response_model=SystemHealth)
async def get_system_health() -> SystemHealth:
    """
    Get overall system health status.

    Returns:
        - status: healthy, degraded, or unhealthy
        - version: Control Plane version
        - uptime_seconds: System uptime in seconds
        - instances_connected: Number of connected OpenClaw instances
        - instances_total: Total number of configured instances
        - active_sessions: Number of active chat sessions
    """
    settings = get_settings()
    collector = get_metrics_collector()
    metrics = collector.get_all_metrics()

    # Determine health status
    instances_connected = metrics["instances"]["connected"]
    instances_total = metrics["instances"]["total"]

    if instances_total == 0:
        status = "healthy"  # No instances configured yet
    elif instances_connected == instances_total:
        status = "healthy"
    elif instances_connected > 0:
        status = "degraded"
    else:
        status = "unhealthy"

    return SystemHealth(
        status=status,
        version=settings.app_version,
        uptime_seconds=time.time() - _start_time,
        instances_connected=instances_connected,
        instances_total=instances_total,
        active_sessions=metrics["sessions"]["active"],
    )


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics() -> SystemMetrics:
    """
    Get system metrics summary.

    Returns:
        - messages_total: Total messages sent
        - messages_per_minute: Message rate
        - avg_latency_ms: Average latency
        - errors_total: Total errors
    """
    collector = get_metrics_collector()
    metrics = collector.get_all_metrics()
    latency_stats = metrics["latency_ms"]

    return SystemMetrics(
        messages_total=metrics["messages"]["total"],
        messages_per_minute=metrics["messages"]["per_minute"],
        avg_latency_ms=latency_stats.get("avg") or 0.0,
        errors_total=metrics["errors"]["total"],
    )


@router.get("/config")
async def get_system_config() -> dict:
    """
    Get system configuration (non-sensitive).

    Returns safe configuration values for debugging.
    """
    settings = get_settings()

    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "host": settings.host,
        "port": settings.port,
        "database_url": "configured" if settings.database_url else "not configured",
        "cors_origins": settings.cors_origins,
    }


@router.get("/status")
async def get_system_status() -> dict:
    """
    Get detailed system status.

    Returns comprehensive status information including
    connection pool stats and component health.
    """
    settings = get_settings()
    collector = get_metrics_collector()
    connector_pool = get_connector_pool()
    metrics = collector.get_all_metrics()

    # Get connector pool status
    all_connectors = connector_pool.get_all_connectors()
    pool_stats = {
        "total_connectors": len(all_connectors),
        "connected": sum(
            1 for c in all_connectors.values()
            if c and c.is_connected
        ),
    }

    return {
        "system": {
            "name": settings.app_name,
            "version": settings.app_version,
            "uptime_seconds": time.time() - _start_time,
            "started_at": datetime.fromtimestamp(_start_time).isoformat(),
        },
        "instances": metrics["instances"],
        "sessions": metrics["sessions"],
        "messages": metrics["messages"],
        "errors": metrics["errors"],
        "latency_ms": metrics["latency_ms"],
        "connector_pool": pool_stats,
    }


@router.post("/reload")
async def reload_system() -> dict:
    """
    Reload system configuration.

    Note: This is a placeholder for future hot-reload functionality.
    Currently requires restart to apply configuration changes.
    """
    return {
        "success": True,
        "message": "Configuration reload requested. Note: Some changes may require restart.",
    }


@router.get("/version")
async def get_version() -> dict:
    """
    Get version information.
    """
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "python_version": "3.11+",  # Could be dynamic
    }


@router.post("/test-push/{session_id}")
async def test_socketio_push(session_id: str) -> dict:
    """
    Test Socket.IO message push to a session.

    This endpoint pushes a test message to all clients subscribed to a session.
    """
    from app.services.socketio_service import push_message_to_session, connected_clients

    test_message = {
        "id": "test-msg-" + str(int(time.time())),
        "session_id": session_id,
        "role": "assistant",
        "content": "This is a test message from Socket.IO push!",
        "created_at": datetime.now().isoformat(),
    }

    pushed = await push_message_to_session(session_id, test_message)

    return {
        "success": pushed,
        "session_id": session_id,
        "connected_clients": len(connected_clients),
        "message": test_message,
    }


@router.get("/socketio-status")
async def get_socketio_status() -> dict:
    """
    Get Socket.IO connection status.
    """
    from app.services.socketio_service import connected_clients

    return {
        "connected_clients_count": len(connected_clients),
        "connected_client_ids": list(connected_clients),
    }
