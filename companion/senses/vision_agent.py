"""
companion/senses/vision_agent.py
===================================
Vision Agent: periodic screen capture → process → VLM analysis pipeline.
Runs as an async background task. Publishes screen context to EventBus.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Callable, Awaitable

from companion.senses.screen_capture import ScreenCapture
from companion.senses.image_processor import ImageProcessor
from companion.utils.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger(__name__)


class VisionAgent:
    """
    Asynchronous screen analysis agent.

    Workflow (runs every `capture_interval` seconds):
    1. Capture screen with mss
    2. Process image (resize + JPEG + MD5 dedup)
    3. If changed: send to VLM via AICortex
    4. Publish result to EventBus
    """

    def __init__(
        self,
        capture_interval: float = 30.0,
        max_width: int = 1280,
        max_height: int = 720,
        jpeg_quality: int = 60,
        vlm_fn: Optional[Callable[[bytes], Awaitable[Optional[str]]]] = None,
    ) -> None:
        """
        Args:
            capture_interval: Seconds between captures.
            max_width: Max screenshot width.
            max_height: Max screenshot height.
            jpeg_quality: JPEG compression quality (1-95).
            vlm_fn: Async callable (image_bytes) → description_str.
        """
        self.capture_interval = capture_interval
        self._screen = ScreenCapture(monitor_index=1)
        self._processor = ImageProcessor(max_width, max_height, jpeg_quality)
        self._vlm_fn = vlm_fn
        self._bus = get_event_bus()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_context: Optional[str] = None
        self._analysis_count: int = 0
        self._error_count: int = 0

    async def start(self) -> None:
        """Start the vision agent background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="vision_agent")
        logger.info(f"VisionAgent started (interval={self.capture_interval}s)")

    async def stop(self) -> None:
        """Stop the vision agent."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("VisionAgent stopped")

    async def _run_loop(self) -> None:
        """Main capture-analyze loop."""
        while self._running:
            try:
                await self._capture_and_analyze()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._error_count += 1
                logger.error(f"VisionAgent error: {exc}", exc_info=True)

            # Wait for next capture interval
            await asyncio.sleep(self.capture_interval)

    async def _capture_and_analyze(self) -> None:
        """Execute one capture-and-analyze cycle."""
        # Capture in thread executor (blocking I/O)
        loop = asyncio.get_event_loop()
        png_bytes = await loop.run_in_executor(None, self._screen.capture_raw)

        if not png_bytes:
            logger.debug("Screen capture returned no data")
            return

        # Process image (blocking but fast, acceptable)
        jpeg_bytes = await loop.run_in_executor(None, self._processor.process, png_bytes)

        if jpeg_bytes is None:
            logger.debug("Frame was duplicate — skipping VLM analysis")
            return

        # Send to VLM
        if self._vlm_fn is None:
            logger.debug("No VLM function configured — skipping analysis")
            return

        try:
            context = await asyncio.wait_for(
                self._vlm_fn(jpeg_bytes),
                timeout=30.0,
            )
            if context:
                self._last_context = context
                self._analysis_count += 1
                logger.debug(f"Screen context: {context[:80]}…")

                # Publish to event bus
                await self._bus.publish(Event(
                    type=EventType.SCREEN_CONTEXT_UPDATED,
                    data=context,
                    source="vision_agent",
                ))
        except asyncio.TimeoutError:
            logger.warning("VLM analysis timed out")
            self._error_count += 1

    @property
    def last_context(self) -> Optional[str]:
        """Most recent screen context description."""
        return self._last_context

    async def capture_once(self) -> Optional[bytes]:
        """Capture a single frame immediately (for on-demand use)."""
        loop = asyncio.get_event_loop()
        png_bytes = await loop.run_in_executor(None, self._screen.capture_raw)
        if not png_bytes:
            return None
        return await loop.run_in_executor(
            None, self._processor.process, png_bytes
        )

    def stats(self) -> dict:
        return {
            "running": self._running,
            "analysis_count": self._analysis_count,
            "error_count": self._error_count,
            "last_context_length": len(self._last_context) if self._last_context else 0,
            "capture_stats": self._processor.stats(),
        }
