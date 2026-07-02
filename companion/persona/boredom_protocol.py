"""
companion/persona/boredom_protocol.py
======================================
Boredom Protocol.
Monitors user inactivity (idle thresholds). If the user is idle >300s,
triggers a boredom event to initiate a proactive conversation starter.
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional, Callable, Awaitable

from companion.utils.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger(__name__)

class BoredomProtocol:
    """
    Tracks elapsed idle time. If no user message (voice or text) occurs
    within boredom_idle_threshold (default 300s), triggers BOREDOM_TRIGGERED.
    """

    def __init__(
        self,
        boredom_idle_threshold: float = 300.0,
        trigger_callback: Optional[Callable[[], Awaitable[None]]] = None
    ) -> None:
        self.threshold = boredom_idle_threshold
        self._trigger_callback = trigger_callback
        self._last_interaction_time = time.monotonic()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._bus = get_event_bus()

        # Subscribe to user inputs to reset the idle timer
        self._bus.subscribe(EventType.USER_TEXT_INPUT, self._reset_timer)
        self._bus.subscribe(EventType.USER_VOICE_INPUT, self._reset_timer)

    async def start(self) -> None:
        """Start monitoring user inactivity."""
        if self._running:
            return
        self._running = True
        self._last_interaction_time = time.monotonic()
        self._task = asyncio.create_task(self._run_loop(), name="boredom_protocol")
        logger.info(f"Boredom protocol started (threshold={self.threshold}s)")

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Boredom protocol stopped")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(5.0)  # Check every 5 seconds
                idle_duration = time.monotonic() - self._last_interaction_time
                if idle_duration >= self.threshold:
                    logger.info(f"User idle for {idle_duration:.1f}s. Triggering boredom protocol...")
                    await self._trigger_boredom()
                    # Reset timer so we don't trigger constantly
                    self._last_interaction_time = time.monotonic()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in Boredom loop: {exc}")

    async def _reset_timer(self, event: Event) -> None:
        """Reset the idle counter on user input."""
        self._last_interaction_time = time.monotonic()
        logger.debug("Boredom idle timer reset due to user interaction")

    async def _trigger_boredom(self) -> None:
        # Publish event
        await self._bus.publish(Event(
            type=EventType.BOREDOM_TRIGGERED,
            data={"idle_time": self.threshold},
            source="boredom_protocol"
        ))
        # Optional direct callback
        if self._trigger_callback:
            try:
                await self._trigger_callback()
            except Exception as exc:
                logger.error(f"Boredom trigger callback error: {exc}")
