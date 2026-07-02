"""
companion/memory/db_schema.py
==============================
SQLite schema definitions for all MyCompanion persistent storage.
Single database file with multiple tables for different data types.
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# SQL statements for table creation
CREATE_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    timestamp   REAL NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    metadata    TEXT DEFAULT '{}'
)
"""

CREATE_FACTS = """
CREATE TABLE IF NOT EXISTS facts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_type   TEXT NOT NULL CHECK(fact_type IN ('preference', 'aversion', 'identity', 'goal', 'memory')),
    content     TEXT NOT NULL,
    confidence  REAL NOT NULL DEFAULT 0.8,
    source      TEXT DEFAULT 'extracted',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    access_count INTEGER DEFAULT 0,
    UNIQUE(fact_type, content)
)
"""

CREATE_IDENTITY = """
CREATE TABLE IF NOT EXISTS identity (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL
)
"""

CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    started_at  REAL NOT NULL,
    ended_at    REAL,
    turn_count  INTEGER DEFAULT 0,
    summary     TEXT,
    mood_state  TEXT DEFAULT '{}'
)
"""

CREATE_DREAM_LOG = """
CREATE TABLE IF NOT EXISTS dream_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_date  TEXT NOT NULL,
    summary     TEXT NOT NULL,
    seeds       TEXT DEFAULT '[]',
    created_at  REAL NOT NULL
)
"""

CREATE_CACHE = """
CREATE TABLE IF NOT EXISTS response_cache (
    cache_key   TEXT PRIMARY KEY,
    response    TEXT NOT NULL,
    model       TEXT NOT NULL,
    created_at  REAL NOT NULL,
    ttl         REAL NOT NULL DEFAULT 3600.0,
    hit_count   INTEGER NOT NULL DEFAULT 0
)
"""

CREATE_PREFERENCES = """
CREATE TABLE IF NOT EXISTS preferences (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    category    TEXT DEFAULT 'general',
    updated_at  REAL NOT NULL
)
"""

ALL_TABLES = [
    CREATE_CONVERSATIONS,
    CREATE_FACTS,
    CREATE_IDENTITY,
    CREATE_SESSIONS,
    CREATE_DREAM_LOG,
    CREATE_CACHE,
    CREATE_PREFERENCES,
]

ALL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type)",
    "CREATE INDEX IF NOT EXISTS idx_cache_created ON response_cache(created_at)",
]


def initialize_database(db_path: Path) -> sqlite3.Connection:
    """
    Create the database and all required tables.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Open sqlite3.Connection with WAL mode enabled.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)

    # Enable WAL for better concurrent performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-8000")  # 8MB cache

    # Create all tables
    for statement in ALL_TABLES:
        conn.execute(statement)
    for idx in ALL_INDEXES:
        conn.execute(idx)

    conn.commit()
    logger.info(f"Database initialized at {db_path}")
    return conn


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a database connection with row_factory set."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
