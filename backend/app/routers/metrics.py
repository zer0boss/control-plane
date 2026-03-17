"""
Metrics API Routes

Prometheus-format metrics export for monitoring.
"""

from fastapi import APIRouter, Response
from app.services.metrics_collector import get_metrics_collector

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_prometheus_metrics() -> Response:
    """
    Get metrics in Prometheus text format.

    Returns:
        Prometheus-formatted metrics including:
        - Message counts and rates
        - Latency statistics (P50, P95, P99)
        - Connection status
        - Error counts
        - Uptime
    """
    collector = get_metrics_collector()
    metrics_text = collector.to_prometheus()

    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@router.get("/json")
async def get_metrics_json() -> dict:
    """
    Get metrics in JSON format.

    Returns all current metrics as a JSON object for easier parsing
    by non-Prometheus clients.
    """
    collector = get_metrics_collector()
    return collector.get_all_metrics()


@router.get("/latency")
async def get_latency_stats() -> dict:
    """
    Get latency statistics.

    Returns P50, P95, P99, and average latency in milliseconds.
    """
    collector = get_metrics_collector()
    return collector.get_latency_stats()


@router.get("/rate")
async def get_message_rate(window_seconds: int = 60) -> dict:
    """
    Get message rate over a time window.

    Args:
        window_seconds: Time window in seconds (default: 60)

    Returns:
        Messages per minute over the specified window.
    """
    collector = get_metrics_collector()
    rate = collector.get_message_rate(window_seconds)
    return {
        "messages_per_minute": rate,
        "window_seconds": window_seconds,
    }
