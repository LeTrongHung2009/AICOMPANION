"""
companion/memory/memory_manager.py
=====================================
Central memory coordinator. Initializes the database and provides
unified access to all memory subsystems (conversations, facts, identity).
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from companion.memory.db_schema import initialize_database, get_connection
from companion.memory.conversation_log import ConversationLog
from companion.memory.fact_store import FactStore, IdentityStore, PreferenceStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Unified interface to all memory subsystems.

    Responsibilities:
    - Initialize and maintain the SQLite database connection
    - Provide access to ConversationLog, FactStore, IdentityStore, PreferenceStore
    - Export memory state for prompt injection
    - Handle graceful shutdown
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.conversations: Optional[ConversationLog] = None
        self.facts: Optional[FactStore] = None
        self.identity: Optional[IdentityStore] = None
        self.preferences: Optional[PreferenceStore] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database and all memory subsystems."""
        if self._initialized:
            return

        # Initialize database (synchronously, it's a one-time setup)
        loop = asyncio.get_event_loop()
        self._conn = await loop.run_in_executor(
            None, initialize_database, self.db_path
        )
        # Use row_factory for better ergonomics
        self._conn.row_factory = sqlite3.Row

        # Wire up subsystems
        self.conversations = ConversationLog(self._conn)
        self.facts = FactStore(self._conn)
        self.identity = IdentityStore(self._conn)
        self.preferences = PreferenceStore(self._conn)

        self._initialized = True
        logger.info("MemoryManager initialized successfully")

    async def get_context_for_prompt(
        self,
        max_history: int = 20,
        max_facts: int = 10,
    ) -> dict:
        """
        Gather all memory context needed for prompt building.

        Returns:
            Dict with 'history', 'facts', 'identity' keys.
        """
        if not self._initialized:
            await self.initialize()

        history = await self.conversations.get_session_history(limit=max_history)
        facts = await self.facts.get_user_facts_for_prompt(limit=max_facts)
        identity = await self.identity.get_all()

        return {
            "history": history,
            "facts": facts,
            "identity": identity,
        }

    async def log_user_message(self, content: str) -> None:
        """Log a user message."""
        await self.conversations.add_message("user", content)

    async def log_assistant_message(self, content: str, tokens: int = 0) -> None:
        """Log an assistant message."""
        await self.conversations.add_message("assistant", content, tokens_used=tokens)

    async def add_learned_facts(self, facts_json: str) -> int:
        """
        Parse and store facts from JSON string (from auto-learner).

        Args:
            facts_json: JSON array string of fact dicts.

        Returns:
            Number of new facts added.
        """
        import json
        try:
            facts_data = json.loads(facts_json)
            if not isinstance(facts_data, list):
                return 0

            added = 0
            for item in facts_data:
                fact_type = item.get("type", "memory")
                content = item.get("fact", "").strip()
                if content:
                    is_new = await self.facts.add_fact(fact_type, content)
                    if is_new:
                        added += 1
            return added
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning(f"Failed to parse facts JSON: {exc}")
            return 0

    async def shutdown(self) -> None:
        """Close the database connection and log session end."""
        if self.conversations:
            await self.conversations.close_session()
        if self._conn:
            self._conn.close()
            logger.info("MemoryManager database connection closed")

    def stats(self) -> dict:
        """Return memory system statistics."""
        return {
            "initialized": self._initialized,
            "db_path": str(self.db_path),
        }
