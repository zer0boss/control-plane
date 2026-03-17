"""
OpenClaw Control Plane - Main Application

FastAPI application for managing multiple OpenClaw instances.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.routers import instances, sessions, messages, metrics, system
from app.connectors.ao_plugin import get_connector_pool

settings = get_settings()


# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """Get current time in Beijing timezone (UTC+8)."""
    return datetime.now(BEIJING_TZ)


def format_beijing(dt: datetime) -> str:
    """Format datetime as Beijing time string with timezone."""
    if dt.tzinfo is None:
        # 数据库中存储的是北京时间，添加时区信息
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"


def log_print(prefix: str, message: str):
    """Print log message with Beijing timestamp."""
    print(f"[{format_beijing(beijing_now())}] {prefix} {message}")


class BeijingTimeJSONResponse(JSONResponse):
    """Custom JSON response that formats datetime as Beijing time with timezone."""

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self._json_serializer,
        ).encode("utf-8")

    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return format_beijing(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    log_print("[STARTED]", f"{settings.app_name} v{settings.app_version} started")
    log_print("[METRICS]", f"Available at http://localhost:{settings.port}/metrics")

    # Reconnect to instances that were connected before shutdown
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import Instance, InstanceStatus
    from app.services.instance_manager import InstanceService
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Instance).where(Instance.status == InstanceStatus.CONNECTED)
        )
        connected_instances = result.scalars().all()

        if connected_instances:
            log_print("[RECONNECT]", f"Found {len(connected_instances)} connected instances, reconnecting...")
            instance_service = InstanceService(db)
            for instance in connected_instances:
                try:
                    # Set status to connecting first
                    instance.status = InstanceStatus.CONNECTING
                    await db.commit()

                    connected = await instance_service.connect_instance(instance.id)
                    if connected:
                        log_print("[RECONNECT]", f"Successfully connected to instance {instance.name} ({instance.id})")
                    else:
                        log_print("[RECONNECT]", f"Failed to connect to instance {instance.name} ({instance.id})")
                except Exception as e:
                    log_print("[RECONNECT]", f"Error connecting to instance {instance.name}: {e}")
                    instance.status = InstanceStatus.ERROR
                    instance.status_message = str(e)
                    await db.commit()

    yield
    # Shutdown
    connector_pool = get_connector_pool()
    await connector_pool.close_all()
    log_print("[SHUTDOWN]", "Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Centralized management platform for multiple OpenClaw instances",
    lifespan=lifespan,
    default_response_class=BeijingTimeJSONResponse,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(instances.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


# Mount Socket.IO for real-time communication
from app.services.socketio_service import sio, get_socket_app

# Create the combined ASGI app with Socket.IO support
# The socket_app handles both HTTP (FastAPI) and WebSocket (Socket.IO) requests
socket_app = get_socket_app(app)

# For uvicorn, use socket_app instead of app
# uvicorn app.main:socket_app --host 0.0.0.0 --port 8000


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:socket_app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
