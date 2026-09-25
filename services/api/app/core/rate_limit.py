"""Lightweight in-memory rate limit for /api/chat."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from app.config import get_settings

_lock = Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def allow_request(client_key: str) -> bool:
    """Return True if the client is under the configured rate limit."""
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return True

    now = time.monotonic()
    window = 60.0
    with _lock:
        bucket = _hits[client_key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def reset_rate_limits() -> None:
    """Test helper."""
    with _lock:
        _hits.clear()
