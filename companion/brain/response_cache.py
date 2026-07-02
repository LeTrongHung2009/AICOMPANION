"""
companion/brain/response_cache.py
===================================
SQLite-backed response cache to avoid duplicate API calls.
Uses SHA-256 hashing of prompt content as cache key.
TTL-based expiration to keep cache fresh.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _hash_prompt(messages: list[dict], model: str) -> str:
    """Generate a stable hash for a set of messages + model."""
    canonical = json.dumps(
        {"model": model, "messages": messages},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ResponseCache:
    """
    SQLite-backed response cache.

    Schema:
        cache_key: TEXT PRIMARY KEY (SHA-256 hash)
        response:  TEXT (JSON-encoded response)
        model:     TEXT
        created_at: REAL (Unix timestamp)
        ttl:       REAL (seconds until expiry)
        hit_count: INTEGER
    """

    CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS response_cache (
            cache_key  TEXT PRIMARY KEY,
            response   TEXT NOT NULL,
            model      TEXT NOT NULL,
            created_at REAL NOT NULL,
            ttl        REAL NOT NULL DEFAULT 3600.0,
            hit_count  INTEGER NOT NULL DEFAULT 0
        )
    """

    def __init__(self, db_path: Path, default_ttl: float = 3600.0) -> None:
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._hits: int = 0
        self._misses: int = 0
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the cache database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(self.CREATE_TABLE)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_created ON response_cache(created_at)"
            )
            conn.commit()
        logger.debug(f"Response cache initialized at {self.db_path}")

    async def get(
        self, messages: list[dict], model: str
    ) -> Optional[str]:
        """
        Retrieve cached response. Returns None on cache miss or expiry.
        """
        cache_key = _hash_prompt(messages, model)
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._get_sync, cache_key
            )

    def _get_sync(self, cache_key: str) -> Optional[str]:
        now = time.time()
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                row = conn.execute(
                    "SELECT response, created_at, ttl FROM response_cache WHERE cache_key = ?",
                    (cache_key,),
                ).fetchone()

                if row is None:
                    self._misses += 1
                    return None

                response, created_at, ttl = row
                if now - created_at > ttl:
                    # Expired — delete it
                    conn.execute(
                        "DELETE FROM response_cache WHERE cache_key = ?",
                        (cache_key,),
                    )
                    conn.commit()
                    self._misses += 1
                    logger.debug(f"Cache expired for key {cache_key[:16]}…")
                    return None

                # Update hit count
                conn.execute(
                    "UPDATE response_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                    (cache_key,),
                )
                conn.commit()
                self._hits += 1
                logger.debug(f"Cache HIT for key {cache_key[:16]}…")
                return response

        except sqlite3.Error as exc:
            logger.error(f"Cache read error: {exc}")
            self._misses += 1
            return None

    async def set(
        self,
        messages: list[dict],
        model: str,
        response: str,
        ttl: Optional[float] = None,
    ) -> None:
        """Store a response in the cache."""
        cache_key = _hash_prompt(messages, model)
        effective_ttl = ttl if ttl is not None else self.default_ttl
        async with self._lock:
            await asyncio.get_event_loop().run_in_executor(
                None, self._set_sync, cache_key, model, response, effective_ttl
            )

    def _set_sync(
        self, cache_key: str, model: str, response: str, ttl: float
    ) -> None:
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO response_cache
                       (cache_key, response, model, created_at, ttl, hit_count)
                       VALUES (?, ?, ?, ?, ?, 0)""",
                    (cache_key, response, model, time.time(), ttl),
                )
                conn.commit()
            logger.debug(f"Cache SET for key {cache_key[:16]}… TTL={ttl}s")
        except sqlite3.Error as exc:
            logger.error(f"Cache write error: {exc}")

    async def purge_expired(self) -> int:
        """Remove all expired cache entries. Returns count deleted."""
        now = time.time()
        async with self._lock:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._purge_sync, now
            )

    def _purge_sync(self, now: float) -> int:
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    "DELETE FROM response_cache WHERE (created_at + ttl) < ?", (now,)
                )
                conn.commit()
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"Purged {deleted} expired cache entries")
                return deleted
        except sqlite3.Error as exc:
            logger.error(f"Cache purge error: {exc}")
            return 0

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("DELETE FROM response_cache")
                conn.commit()
        logger.info("Response cache cleared")

    def stats(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM response_cache").fetchone()[0]
        except Exception:
            count = 0
        return {
            "cache_hits": self._hits,
            "cache_misses": self._misses,
            "hit_rate_percent": round(hit_rate, 1),
            "entries_in_db": count,
        }
