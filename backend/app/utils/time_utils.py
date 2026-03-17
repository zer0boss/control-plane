"""
Time utilities for Beijing timezone (UTC+8)
"""

from datetime import datetime, timezone, timedelta

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """Get current time in Beijing timezone (UTC+8)."""
    return datetime.now(BEIJING_TZ)


def beijing_now_naive() -> datetime:
    """Get current Beijing time as naive datetime (for database storage)."""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


def format_beijing_time(dt: datetime) -> str:
    """Format datetime as Beijing time string."""
    if dt.tzinfo is None:
        # Assume naive datetime is Beijing time
        dt = dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(BEIJING_TZ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"


def to_beijing_time(dt: datetime) -> datetime:
    """Convert datetime to Beijing timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetime is UTC, convert to Beijing
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ)
