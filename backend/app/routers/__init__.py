"""
API Routers Package

All FastAPI routers for the Control Plane API.
"""

from app.routers.instances import router as instances_router
from app.routers.sessions import router as sessions_router
from app.routers.messages import router as messages_router
from app.routers.metrics import router as metrics_router
from app.routers.system import router as system_router
from app.routers.tasks import router as tasks_router
from app.routers.meetings import router as meetings_router

__all__ = [
    "instances_router",
    "sessions_router",
    "messages_router",
    "metrics_router",
    "system_router",
    "tasks_router",
    "meetings_router",
]
