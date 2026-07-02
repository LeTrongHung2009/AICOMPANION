"""
companion/senses/stt_pipeline.py
===================================
Speech-to-Text pipeline. Coordinates microphone capture with
Groq Whisper transcription. Publishes results to EventBus.
Runs as a background async task.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Callable, Awaitable

from companion.senses.mic_capture import MicCapture
from companion.utils.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger(__name__)


class STTPipeline:
    """
    Continuous Speech-to-Text pipeline.

    Loop:
    1. Capture audio utterance from mic (async, non-blocking)
    2. Send WAV bytes to Groq Whisper
    3. Publish transcription result to EventBus as USER_VOICE_INPUT
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration: float = 5.0,
        silence_threshold: float = 0.01,
        language: str = "vi",
        transcribe_fn: Optional[Callable[[bytes, str], Awaitable[Optional[str]]]] = None,
    ) -> None:
        self._mic = MicCapture(
            sample_rate=sample_rate,
            channels=1,
            chunk_duration=chunk_duration,
            silence_threshold=silence_threshold,
        )
        self.language = language
        self._transcribe_fn = transcribe_fn
        self._bus = get_event_bus()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._transcription_count: int = 0
        self._last_activity: float = time.monotonic()

    async def start(self) -> None:
        """Start the STT background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="stt_pipeline")
        logger.info("STT Pipeline started")

    async def stop(self) -> None:
        """Stop the STT pipeline."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("STT Pipeline stopped")

    async def _run_loop(self) -> None:
        """Continuous capture and transcription loop."""
        while self._running:
            try:
                await self._capture_and_transcribe()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"STT loop error: {exc}", exc_info=True)
                await asyncio.sleep(2.0)  # Brief pause on error

    async def _capture_and_transcribe(self) -> None:
        """Single capture→transcribe cycle."""
        if self._transcribe_fn is None:
            await asyncio.sleep(1.0)
            return

        # Capture utterance (blocks until speech + silence)
        audio_bytes = await self._mic.capture_utterance(
            max_silence_duration=1.5,
            max_total_duration=30.0,
        )

        if not audio_bytes:
            return

        # Transcribe via Groq Whisper
        try:
            text = await asyncio.wait_for(
                self._transcribe_fn(audio_bytes, self.language),
                timeout=20.0,
            )
        except asyncio.TimeoutError:
            logger.warning("STT transcription timed out")
            return

        if not text or len(text.strip()) < 2:
            return

        text = text.strip()
        self._transcription_count += 1
        self._last_activity = time.monotonic()
        logger.info(f"STT transcription: '{text[:80]}'")

        # Publish to event bus for orchestrator handling
        await self._bus.publish(Event(
            type=EventType.USER_VOICE_INPUT,
            data=text,
            source="stt_pipeline",
        ))

    @property
    def last_activity(self) -> float:
        return self._last_activity

    def stats(self) -> dict:
        return {
            "running": self._running,
            "transcription_count": self._transcription_count,
            "language": self.language,
        }
