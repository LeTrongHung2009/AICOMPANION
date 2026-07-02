"""
companion/memory/fact_store.py
================================
Stores extracted user facts (preferences, identity, goals, aversions).
Provides fuzzy deduplication to avoid redundant entries.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from typing import Optional

logger = logging.getLogger(__name__)

VALID_FACT_TYPES = {"preference", "aversion", "identity", "goal", "memory"}


class FactStore:
    """
    Persistent storage for extracted user facts.
    Supports typed facts with confidence scores.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = asyncio.Lock()

    async def add_fact(
        self,
        fact_type: str,
        content: str,
        confidence: float = 0.8,
        source: str = "extracted",
    ) -> bool:
        """
        Add or update a fact. Deduplicates by (type, content).

        Args:
            fact_type: One of preference, aversion, identity, goal, memory.
            content: The fact text.
            confidence: Confidence score (0.0–1.0).
            source: Where this fact came from.

        Returns:
            True if fact was new, False if updated.
        """
        if fact_type not in VALID_FACT_TYPES:
            logger.warning(f"Invalid fact type: {fact_type}")
            return False
        if not content.strip():
            return False

        now = time.time()
        async with self._lock:
            try:
                # Check if similar fact exists
                existing = self._conn.execute(
                    "SELECT id, confidence FROM facts WHERE fact_type=? AND content=?",
                    (fact_type, content.strip()),
                ).fetchone()

                if existing:
                    # Update confidence and access time
                    new_confidence = min(1.0, existing[1] + 0.05)  # Small confidence bump
                    self._conn.execute(
                        "UPDATE facts SET confidence=?, updated_at=? WHERE id=?",
                        (new_confidence, now, existing[0]),
                    )
                    self._conn.commit()
                    return False
                else:
                    self._conn.execute(
                        """INSERT INTO facts (fact_type, content, confidence, source, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (fact_type, content.strip(), confidence, source, now, now),
                    )
                    self._conn.commit()
                    logger.info(f"New fact [{fact_type}]: {content[:60]}")
                    return True
            except sqlite3.Error as exc:
                logger.error(f"Failed to add fact: {exc}")
                return False

    async def get_facts(
        self,
        fact_type: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> list[dict]:
        """
        Retrieve stored facts.

        Args:
            fact_type: Optional filter by type.
            min_confidence: Minimum confidence threshold.
            limit: Maximum results.

        Returns:
            List of fact dictionaries.
        """
        async with self._lock:
            try:
                if fact_type:
                    rows = self._conn.execute(
                        """SELECT fact_type, content, confidence, source, created_at
                           FROM facts WHERE fact_type=? AND confidence>=?
                           ORDER BY confidence DESC, access_count DESC LIMIT ?""",
                        (fact_type, min_confidence, limit),
                    ).fetchall()
                else:
                    rows = self._conn.execute(
                        """SELECT fact_type, content, confidence, source, created_at
                           FROM facts WHERE confidence>=?
                           ORDER BY confidence DESC, access_count DESC LIMIT ?""",
                        (min_confidence, limit),
                    ).fetchall()

                return [
                    {"type": r[0], "content": r[1], "confidence": r[2],
                     "source": r[3], "created_at": r[4]}
                    for r in rows
                ]
            except sqlite3.Error as exc:
                logger.error(f"Failed to get facts: {exc}")
                return []

    async def get_user_facts_for_prompt(self, limit: int = 10) -> list[str]:
        """
        Get facts formatted as strings for system prompt injection.
        Returns highest-confidence facts across all types.
        """
        facts = await self.get_facts(limit=limit)
        return [f["content"] for f in facts]

    async def delete_fact(self, fact_id: int) -> bool:
        """Delete a fact by ID."""
        async with self._lock:
            try:
                self._conn.execute("DELETE FROM facts WHERE id=?", (fact_id,))
                self._conn.commit()
                return True
            except sqlite3.Error:
                return False

    async def count_by_type(self) -> dict[str, int]:
        """Return count of facts per type."""
        try:
            rows = self._conn.execute(
                "SELECT fact_type, COUNT(*) FROM facts GROUP BY fact_type"
            ).fetchall()
            return {r[0]: r[1] for r in rows}
        except sqlite3.Error:
            return {}


class IdentityStore:
    """
    Key-value store for user identity attributes.
    Examples: name, occupation, location, language preference.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: str) -> None:
        """Set an identity attribute."""
        async with self._lock:
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO identity (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, time.time()),
                )
                self._conn.commit()
            except sqlite3.Error as exc:
                logger.error(f"Identity set failed: {exc}")

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an identity attribute."""
        async with self._lock:
            try:
                row = self._conn.execute(
                    "SELECT value FROM identity WHERE key=?", (key,)
                ).fetchone()
                return row[0] if row else default
            except sqlite3.Error:
                return default

    async def get_all(self) -> dict[str, str]:
        """Get all identity attributes."""
        async with self._lock:
            try:
                rows = self._conn.execute("SELECT key, value FROM identity").fetchall()
                return {r[0]: r[1] for r in rows}
            except sqlite3.Error:
                return {}


class PreferenceStore:
    """
    Structured user preference storage with categorization.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: str, category: str = "general") -> None:
        """Set a preference."""
        async with self._lock:
            try:
                self._conn.execute(
                    """INSERT OR REPLACE INTO preferences (key, value, category, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (key, value, category, time.time()),
                )
                self._conn.commit()
            except sqlite3.Error as exc:
                logger.error(f"Preference set failed: {exc}")

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a preference by key."""
        async with self._lock:
            try:
                row = self._conn.execute(
                    "SELECT value FROM preferences WHERE key=?", (key,)
                ).fetchone()
                return row[0] if row else default
            except sqlite3.Error:
                return default

    async def get_by_category(self, category: str) -> dict[str, str]:
        """Get all preferences in a category."""
        async with self._lock:
            try:
                rows = self._conn.execute(
                    "SELECT key, value FROM preferences WHERE category=?", (category,)
                ).fetchall()
                return {r[0]: r[1] for r in rows}
            except sqlite3.Error:
                return {}
