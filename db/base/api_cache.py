"""
Unified SQLite-backed API response cache for db/ scripts.

Replaces the per-script JSON file caches in mb_artist_info.py and
lastfm_escuchas.py with a single shared store.

Usage:
    cache = APICache("db/.cache/api_responses.sqlite")

    # Read (returns None on miss or expiry)
    data = cache.get(("artist_name", "The Cure"), service="musicbrainz")

    # Write
    cache.set(("artist_name", "The Cure"), service="musicbrainz", value={...})

    # Invalidate one entry
    cache.invalidate(("artist_name", "The Cure"), service="musicbrainz")

    # Drop a whole service (e.g. to force re-fetch after API changes)
    cache.clear_service("spotify")
"""

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

# Default TTL in days per service
_DEFAULT_TTL: dict[str, int] = {
    "musicbrainz": 30,
    "spotify": 7,
    "youtube": 7,
    "discogs": 30,
    "lastfm": 7,
    "listenbrainz": 3,
    "bandcamp": 14,
    "rateyourmusic": 14,
    "default": 14,
}

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS cache (
    key      TEXT    NOT NULL,
    service  TEXT    NOT NULL,
    value    TEXT    NOT NULL,
    expires  REAL    NOT NULL,
    PRIMARY KEY (key, service)
)
"""
_CREATE_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_cache_svc "
    "ON cache (service, expires)"
)


def _make_key(parts: Any) -> str:
    """Stable SHA-256 key from any JSON-serialisable value."""
    if isinstance(parts, str):
        return parts
    raw = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


class APICache:
    """
    Thread-safe SQLite-backed cache with per-service TTL.

    Compatible with the old mb_artist_info.APICache interface:
        cache.get(key_parts)   → use service='default'
        cache.put(key_parts, value)

    And the richer new interface:
        cache.get(key_parts, service='spotify')
        cache.set(key_parts, service='spotify', value=...)
    """

    def __init__(
        self,
        cache_path: str | Path,
        ttl_override: dict[str, int] | None = None,
    ):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        self.ttl = dict(_DEFAULT_TTL)
        if ttl_override:
            self.ttl.update(ttl_override)

        self._lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers

    def _init_db(self) -> None:
        with self._lock:
            with sqlite3.connect(str(self.cache_path)) as conn:
                conn.execute(_CREATE_TABLE)
                conn.execute(_CREATE_IDX)
                conn.execute(
                    "DELETE FROM cache WHERE expires < ?", (time.time(),)
                )

    def _ttl_days(self, service: str) -> int:
        return self.ttl.get(service, self.ttl["default"])

    # ------------------------------------------------------------------
    # Public API

    def get(
        self,
        key_parts: Any,
        service: str = "default",
    ) -> Optional[Any]:
        """Return cached value or None if missing/expired."""
        key = _make_key(key_parts)
        with self._lock:
            with sqlite3.connect(str(self.cache_path)) as conn:
                row = conn.execute(
                    "SELECT value FROM cache "
                    "WHERE key=? AND service=? AND expires>?",
                    (key, service, time.time()),
                ).fetchone()
        return json.loads(row[0]) if row else None

    def set(
        self,
        key_parts: Any,
        service: str = "default",
        value: Any = None,
        ttl_days: int | None = None,
    ) -> None:
        """Store value, overwriting any existing entry."""
        key = _make_key(key_parts)
        days = ttl_days or self._ttl_days(service)
        expires = time.time() + days * 86400
        with self._lock:
            with sqlite3.connect(str(self.cache_path)) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, service, value, expires) "
                    "VALUES (?,?,?,?)",
                    (key, service, json.dumps(value, default=str), expires),
                )

    # Alias for backward-compat with mb_artist_info.APICache.put()
    def put(self, key_parts: Any, value: Any, service: str = "default") -> None:
        self.set(key_parts, service=service, value=value)

    def invalidate(
        self,
        key_parts: Any,
        service: str | None = None,
    ) -> None:
        """Remove one entry (or all services for that key)."""
        key = _make_key(key_parts)
        with self._lock:
            with sqlite3.connect(str(self.cache_path)) as conn:
                if service:
                    conn.execute(
                        "DELETE FROM cache WHERE key=? AND service=?",
                        (key, service),
                    )
                else:
                    conn.execute("DELETE FROM cache WHERE key=?", (key,))

    def clear_service(self, service: str) -> None:
        """Drop all cached entries for a given service."""
        with self._lock:
            with sqlite3.connect(str(self.cache_path)) as conn:
                conn.execute("DELETE FROM cache WHERE service=?", (service,))

    def stats(self) -> dict[str, int]:
        """Return entry counts per service (for debugging)."""
        with sqlite3.connect(str(self.cache_path)) as conn:
            rows = conn.execute(
                "SELECT service, COUNT(*) FROM cache WHERE expires>? "
                "GROUP BY service",
                (time.time(),),
            ).fetchall()
        return {r[0]: r[1] for r in rows}
