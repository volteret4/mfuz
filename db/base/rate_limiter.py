"""
Per-service token-bucket rate limiters for db/ scripts.

Usage:
    from db.base.rate_limiter import get_limiter

    get_limiter("musicbrainz").wait()   # blocks until token available
    result = musicbrainzngs.search_artists(...)

Default limits (calls per second):
    musicbrainz  → 1.0  (strict server policy)
    discogs      → 1.0  (60 req/min authenticated)
    spotify      → 10.0
    lastfm       → 5.0
    youtube      → 5.0
    bandcamp     → 2.0
    listenbrainz → 5.0
"""

import threading
import time
from typing import Dict

_SERVICE_LIMITS: Dict[str, float] = {
    "musicbrainz": 1.0,
    "discogs": 1.0,
    "spotify": 10.0,
    "lastfm": 5.0,
    "youtube": 5.0,
    "bandcamp": 2.0,
    "listenbrainz": 5.0,
    "default": 2.0,
}


class RateLimiter:
    """
    Simple token-bucket rate limiter (1 token at a time).

    Calling .wait() blocks the current thread until at least
    min_interval seconds have elapsed since the last call.
    Thread-safe.
    """

    def __init__(self, calls_per_second: float):
        if calls_per_second <= 0:
            raise ValueError("calls_per_second must be positive")
        self.min_interval: float = 1.0 / calls_per_second
        self._lock = threading.Lock()
        self._last_call: float = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_call = time.monotonic()

    @property
    def calls_per_second(self) -> float:
        return 1.0 / self.min_interval


# Module-level singletons per service
_limiters: Dict[str, RateLimiter] = {}
_registry_lock = threading.Lock()


def get_limiter(service: str) -> RateLimiter:
    """
    Return the shared RateLimiter for a given service, creating it on first use.

    Example:
        get_limiter("musicbrainz").wait()
    """
    with _registry_lock:
        if service not in _limiters:
            rate = _SERVICE_LIMITS.get(service, _SERVICE_LIMITS["default"])
            _limiters[service] = RateLimiter(rate)
        return _limiters[service]


def set_limit(service: str, calls_per_second: float) -> None:
    """Override the rate for a service (affects all future .wait() calls)."""
    with _registry_lock:
        _limiters[service] = RateLimiter(calls_per_second)
