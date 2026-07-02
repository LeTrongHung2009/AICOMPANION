"""
companion/memory/conversation_log.py
======================================
Stores and retrieves conversation history.
Supports session-based grouping and history trimming.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class ConversationLog:
    """
    Manages conversation history in SQLite.
    Groups messages by session ID (one session per runtime).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = asyncio.Lock()
        self._session_id = str(uuid.uuid4())
        self._turn_count = 0
        self._session_started_at = time.time()
        self._init_session()

    def _init_session(self) -> None:
        """Register current session in database."""
        try:
            self._conn.execute(
                "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
                (self._session_id, self._session_started_at),
            )
            self._conn.commit()
            logger.info(f"New session started: {self._session_id[:8]}…")
        except sqlite3.Error as exc:
            logger.error(f"Failed to init session: {exc}")

    @property
    def session_id(self) -> str:
        return self._session_id

    async def add_message(
        self,
        role: str,
        content: str,
        tokens_used: int = 0,
        metadata: Optional[dict] = None,
    ) -> int:
        """
        Add a message to the conversation log.

        Args:
            role: 'user' or 'assistant'.
            content: Message text.
            tokens_used: Token count for this message.
            metadata: Optional metadata dict.

        Returns:
            Row ID of inserted message.
        """
        import json
        meta_str = json.dumps(metadata or {})
        async with self._lock:
            try:
                cursor = self._conn.execute(
                    """INSERT INTO conversations
                       (session_id, role, content, timestamp, tokens_used, metadata)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (self._session_id, role, content, time.time(), tokens_used, meta_str),
                )
                self._conn.commit()
                self._turn_count += 1
                return cursor.lastrowid or 0
            except sqlite3.Error as exc:
                logger.error(f"Failed to log message: {exc}")
                return 0

    async def get_session_history(
        self,
        limit: int = 50,
        as_messages: bool = True,
    ) -> list:
        """
        Get recent messages from the current session.

        Args:
            limit: Maximum number of messages to return.
            as_messages: If True, returns OpenAI-style {role, content} dicts.

        Returns:
            List of message dicts or Row objects.
        """
        async with self._lock:
            try:
                rows = self._conn.execute(
                    """SELECT role, content, timestamp FROM conversations
                       WHERE session_id = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (self._session_id, limit),
                ).fetchall()
                rows = list(reversed(rows))  # Chronological order

                if as_messages:
                    return [{"role": r[0], "content": r[1]} for r in rows]
                return rows
            except sqlite3.Error as exc:
                logger.error(f"Failed to get history: {exc}")
                return []

    async def get_all_today(self) -> list[dict]:
        """Get all conversations from today (for dream engine)."""
        import datetime
        today_start = time.mktime(datetime.date.today().timetuple())
        async with self._lock:
            try:
                rows = self._conn.execute(
                    """SELECT role, content, timestamp FROM conversations
                       WHERE timestamp >= ?
                       ORDER BY timestamp ASC""",
                    (today_start,),
                ).fetchall()
                return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
            except sqlite3.Error as exc:
                logger.error(f"Failed to get today's conversations: {exc}")
                return []

    async def close_session(self, summary: Optional[str] = None) -> None:
        """Mark the current session as ended."""
        async with self._lock:
            try:
                self._conn.execute(
                    """UPDATE sessions SET ended_at=?, turn_count=?, summary=?
                       WHERE id=?""",
                    (time.time(), self._turn_count, summary, self._session_id),
                )
                self._conn.commit()
                logger.info(f"Session {self._session_id[:8]}… closed ({self._turn_count} turns)")
            except sqlite3.Error as exc:
                logger.error(f"Failed to close session: {exc}")

    async def count_today_turns(self) -> int:
        """Count conversation turns made today."""
        import datetime
        today_start = time.mktime(datetime.date.today().timetuple())
        try:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE timestamp >= ?",
                (today_start,),
            ).fetchone()
            return row[0] if row else 0
        except sqlite3.Error:
            return 0
