"""
companion/dream/dream_engine.py
===============================
Dream Engine.
Triggers memory consolidation and seed generation cycles when the system is idle (>600s).
Consolidates short-term session logs into SQLite facts tables.
"""

from __future__ import annotations

import asyncio
import time
import logging
import sqlite3
from datetime import date
from typing import Optional, Callable, Awaitable

from companion.dream.log_compressor import LogCompressor
from companion.dream.memory_synthesizer import MemorySynthesizer
from companion.dream.seed_generator import SeedGenerator
from companion.utils.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger(__name__)

class DreamEngine:
    """
    Background worker loop. Monitors user interaction activity.
    Saves consolidation summaries in SQLite dream_log table.
    """

    def __init__(
        self,
        db_conn: sqlite3.Connection,
        get_logs_fn: Callable[[], Awaitable[list[dict]]],
        synthesis_fn: Callable[[str], Awaitable[Optional[str]]],
        save_fact_fn: Callable[[str, str, float, str], Awaitable[bool]],
        dream_idle_threshold: float = 600.0,
        cycle_duration: float = 600.0  # 10 minutes (600s)
    ) -> None:
        self.db = db_conn
        self._get_logs = get_logs_fn
        self.threshold = dream_idle_threshold
        self.cycle_duration = cycle_duration
        self._bus = get_event_bus()

        # Build sub components
        self.synthesizer = MemorySynthesizer(synthesis_fn, save_fact_fn)
        self.seed_gen = SeedGenerator(synthesis_fn)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_interaction_time = time.monotonic()
        self._dream_active = False

        # Reset idle timer on inputs
        self._bus.subscribe(EventType.USER_TEXT_INPUT, self._reset_timer)
        self._bus.subscribe(EventType.USER_VOICE_INPUT, self._reset_timer)

    async def start(self) -> None:
        """Start the background dream engine."""
        if self._running:
            return
        self._running = True
        self._last_interaction_time = time.monotonic()
        self._task = asyncio.create_task(self._run_loop(), name="dream_engine")
        logger.info(f"Dream Engine active (threshold={self.threshold}s, cycle={self.cycle_duration}s)")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Dream Engine stopped.")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(15.0)  # Check periodically
                idle_duration = time.monotonic() - self._last_interaction_time

                if idle_duration >= self.threshold and not self._dream_active:
                    logger.info(f"Inactivity reached dream threshold ({idle_duration:.1f}s). Starting dream cycle...")
                    await self._dream_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in Dream loop: {exc}")

    async def _reset_timer(self, event: Event) -> None:
        self._last_interaction_time = time.monotonic()
        if self._dream_active:
            self._dream_active = False
            logger.info("Dream cycle interrupted by user activity.")
            await self._bus.publish(Event(EventType.DREAM_ENDED, data={"status": "interrupted"}, source="dream_engine"))

    async def _dream_cycle(self) -> None:
        self._dream_active = True
        await self._bus.publish(Event(EventType.DREAM_STARTED, source="dream_engine"))

        try:
            # 1. Fetch today's conversation logs
            logs = await self._get_logs()
            if not logs:
                logger.info("Dream cycle skipped: no conversation logs found today.")
                self._dream_active = False
                return

            # 2. Compress logs to transcript
            compressed = LogCompressor.compress_logs(logs)

            # 3. Consolidate memory facts
            summary = await self.synthesizer.consolidate_day(compressed)
            if not summary:
                self._dream_active = False
                return

            # 4. Generate next-session dialogue seeds
            seeds = await self.seed_gen.generate_tomorrow_seeds(summary)

            # 5. Persist consolidated cycle details in SQLite
            import json
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_dream_log, summary, seeds)

            await self._bus.publish(Event(
                type=EventType.MEMORY_CONSOLIDATED,
                data={"summary": summary, "seeds": seeds},
                source="dream_engine"
            ))

        except Exception as exc:
            logger.error(f"Error during consolidation dream cycle: {exc}")
        finally:
            self._dream_active = False
            await self._bus.publish(Event(EventType.DREAM_ENDED, data={"status": "completed"}, source="dream_engine"))

    def _save_dream_log(self, summary: str, seeds: list[str]) -> None:
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT INTO dream_log (cycle_date, summary, seeds, created_at) VALUES (?, ?, ?, ?)",
                (date.today().isoformat(), summary, json.dumps(seeds), time.time())
            )
            self.db.commit()
            logger.info("Dream log entries persisted to SQLite database.")
        except Exception as exc:
            logger.error(f"Failed to save dream log entry: {exc}")
