"""
Metrics Collector Service

Collects and exposes Prometheus-format metrics for the Control Plane.
"""

import time
from typing import Optional
from collections import deque
from dataclasses import dataclass, field
from threading import Lock

from app.utils.time_utils import beijing_now


@dataclass
class LatencyRecord:
    """Latency measurement record."""
    value_ms: float
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """
    Collector for Control Plane metrics.

    Tracks:
    - Message counts and rates
    - Latency statistics (P50, P95, P99)
    - Connection status
    - Error counts
    """

    def __init__(self, max_latency_history: int = 10000):
        self._lock = Lock()
        self._start_time = time.time()

        # Message counters
        self._messages_total = 0
        self._messages_success = 0
        self._messages_failed = 0

        # Error counters
        self._errors_total = 0
        self._connection_errors = 0

        # Latency tracking (circular buffer)
        self._latency_history: deque[LatencyRecord] = deque(maxlen=max_latency_history)

        # Instance stats
        self._instances_connected = 0
        self._instances_total = 0
        self._active_sessions = 0

        # Last update times
        self._last_message_time: Optional[float] = None
        self._last_error_time: Optional[float] = None

    # ========================================================================
    # Recording Methods
    # ========================================================================

    def record_message_sent(self, latency_ms: Optional[float] = None, success: bool = True):
        """Record a message being sent."""
        with self._lock:
            self._messages_total += 1
            self._last_message_time = time.time()

            if success:
                self._messages_success += 1
            else:
                self._messages_failed += 1

            if latency_ms is not None and latency_ms > 0:
                self._latency_history.append(LatencyRecord(latency_ms))

    def record_error(self, error_type: str = "general"):
        """Record an error occurrence."""
        with self._lock:
            self._errors_total += 1
            self._last_error_time = time.time()

            if error_type == "connection":
                self._connection_errors += 1

    def record_connection_change(self, connected: int, total: int):
        """Update instance connection counts."""
        with self._lock:
            self._instances_connected = connected
            self._instances_total = total

    def record_session_change(self, active_sessions: int):
        """Update active session count."""
        with self._lock:
            self._active_sessions = active_sessions

    def record_latency(self, latency_ms: float):
        """Record a latency measurement."""
        with self._lock:
            if latency_ms > 0:
                self._latency_history.append(LatencyRecord(latency_ms))

    # ========================================================================
    # Query Methods
    # ========================================================================

    def get_message_rate(self, window_seconds: int = 60) -> float:
        """Calculate messages per minute over the given window."""
        with self._lock:
            cutoff = time.time() - window_seconds
            recent = [r for r in self._latency_history if r.timestamp >= cutoff]

            if not recent:
                return 0.0

            return len(recent) / (window_seconds / 60)

    def get_latency_stats(self) -> dict[str, Optional[float]]:
        """Calculate latency percentiles."""
        with self._lock:
            if not self._latency_history:
                return {"p50": None, "p95": None, "p99": None, "avg": None}

            sorted_latencies = sorted(r.value_ms for r in self._latency_history)
            n = len(sorted_latencies)

            def percentile(p: float) -> float:
                idx = int(n * p / 100)
                return sorted_latencies[min(idx, n - 1)]

            return {
                "p50": percentile(50),
                "p95": percentile(95),
                "p99": percentile(99),
                "avg": sum(sorted_latencies) / n,
            }

    def get_all_metrics(self) -> dict:
        """Get all current metrics."""
        with self._lock:
            uptime = time.time() - self._start_time
            latency_stats = self._get_latency_stats_unlocked()

            return {
                "uptime_seconds": uptime,
                "messages": {
                    "total": self._messages_total,
                    "success": self._messages_success,
                    "failed": self._messages_failed,
                    "per_minute": self._get_message_rate_unlocked(60),
                },
                "latency_ms": latency_stats,
                "errors": {
                    "total": self._errors_total,
                    "connection": self._connection_errors,
                },
                "instances": {
                    "connected": self._instances_connected,
                    "total": self._instances_total,
                },
                "sessions": {
                    "active": self._active_sessions,
                },
                "timestamps": {
                    "last_message": self._last_message_time,
                    "last_error": self._last_error_time,
                },
            }

    # ========================================================================
    # Prometheus Format Export
    # ========================================================================

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        with self._lock:
            lines = []
            now = beijing_now().isoformat()

            # Help and type annotations
            lines.append("# HELP openclaw_messages_total Total messages sent")
            lines.append("# TYPE openclaw_messages_total counter")
            lines.append(f'openclaw_messages_total{{status="success"}} {self._messages_success}')
            lines.append(f'openclaw_messages_total{{status="failed"}} {self._messages_failed}')

            lines.append("# HELP openclaw_errors_total Total errors")
            lines.append("# TYPE openclaw_errors_total counter")
            lines.append(f"openclaw_errors_total {self._errors_total}")

            lines.append("# HELP openclaw_instances Number of OpenClaw instances")
            lines.append("# TYPE openclaw_instances gauge")
            lines.append(f'openclaw_instances{{status="connected"}} {self._instances_connected}')
            lines.append(f'openclaw_instances{{status="total"}} {self._instances_total}')

            lines.append("# HELP openclaw_sessions_active Number of active chat sessions")
            lines.append("# TYPE openclaw_sessions_active gauge")
            lines.append(f"openclaw_sessions_active {self._active_sessions}")

            lines.append("# HELP openclaw_uptime_seconds Control Plane uptime")
            lines.append("# TYPE openclaw_uptime_seconds gauge")
            lines.append(f"openclaw_uptime_seconds {time.time() - self._start_time}")

            # Latency histogram
            latency_stats = self._get_latency_stats_unlocked()
            lines.append("# HELP openclaw_latency_ms Message latency in milliseconds")
            lines.append("# TYPE openclaw_latency_ms summary")

            for bucket in [10, 50, 100, 250, 500, 1000, 2500, 5000]:
                count = sum(1 for r in self._latency_history if r.value_ms <= bucket)
                lines.append(f'openclaw_latency_ms_bucket{{le="{bucket}"}} {count}')
            lines.append(f'openclaw_latency_ms_bucket{{le="+Inf"}} {len(self._latency_history)}')

            if latency_stats["avg"] is not None:
                lines.append(f"openclaw_latency_ms_sum {sum(r.value_ms for r in self._latency_history)}")
                lines.append(f"openclaw_latency_ms_count {len(self._latency_history)}")
                lines.append(f'openclaw_latency_ms{{quantile="0.5"}} {latency_stats["p50"]}')
                lines.append(f'openclaw_latency_ms{{quantile="0.95"}} {latency_stats["p95"]}')
                lines.append(f'openclaw_latency_ms{{quantile="0.99"}} {latency_stats["p99"]}')

            return "\n".join(lines)

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    def _get_latency_stats_unlocked(self) -> dict[str, Optional[float]]:
        """Calculate latency percentiles (must hold lock)."""
        if not self._latency_history:
            return {"p50": None, "p95": None, "p99": None, "avg": None}

        sorted_latencies = sorted(r.value_ms for r in self._latency_history)
        n = len(sorted_latencies)

        def percentile(p: float) -> float:
            idx = int(n * p / 100)
            return sorted_latencies[min(idx, n - 1)]

        return {
            "p50": percentile(50),
            "p95": percentile(95),
            "p99": percentile(99),
            "avg": sum(sorted_latencies) / n,
        }

    def _get_message_rate_unlocked(self, window_seconds: int) -> float:
        """Calculate messages per minute (must hold lock)."""
        cutoff = time.time() - window_seconds
        recent = [r for r in self._latency_history if r.timestamp >= cutoff]

        if not recent:
            return 0.0

        return len(recent) / (window_seconds / 60)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector():
    """Reset metrics collector (for testing)."""
    global _metrics_collector
    _metrics_collector = MetricsCollector()
