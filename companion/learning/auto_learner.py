"""
companion/learning/auto_learner.py
==================================
Auto Learner Orchestrator.
Subscribes to EventBus chat inputs, executes fast Regex scanning,
and triggers asynchronous background LLM extractions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable, Awaitable

from companion.learning.regex_extractor import RegexExtractor
from companion.learning.llm_extractor import LLMExtractor
from companion.utils.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger(__name__)

class AutoLearner:
    """
    Subscribes to dialogue streams.
    Learns and registers user facts in memory.
    """

    def __init__(
        self,
        save_fact_fn: Callable[[str, str, float, str], Awaitable[bool]],
        llm_extract_fn: Optional[Callable[[str], Awaitable[Optional[str]]]] = None
    ) -> None:
        """
        Args:
            save_fact_fn: Async callback to save fact objects (type, content, confidence, source)
            llm_extract_fn: Async callback to invoke AI Cortex prompt extraction.
        """
        self._save_fact = save_fact_fn
        self._llm_extractor = LLMExtractor(llm_extract_fn) if llm_extract_fn else None
        self._bus = get_event_bus()

        # Buffer conversations to avoid calling LLM on every single message
        self._message_buffer: list[str] = []
        self._buffer_lock = asyncio.Lock()
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False

        # Subscribe to chat widget outputs
        self._bus.subscribe(EventType.USER_TEXT_INPUT, self._on_user_message)
        self._bus.subscribe(EventType.USER_VOICE_INPUT, self._on_user_message)

    async def start(self) -> None:
        """Start auto learner loop."""
        self._running = True
        self._processing_task = asyncio.create_task(self._buffer_processing_loop(), name="auto_learner")
        logger.info("Auto Learner active.")

    async def stop(self) -> None:
        self._running = False
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Auto Learner stopped.")

    async def _on_user_message(self, event: Event) -> None:
        text = str(event.data)
        
        # 1. Immediate Regex scanning
        regex_facts = RegexExtractor.extract_facts(text)
        for fact in regex_facts:
            await self._save_fact(fact["type"], fact["fact"], fact["confidence"], "regex_extractor")
            # Publish event
            await self._bus.publish(Event(
                type=EventType.FACT_LEARNED,
                data=fact,
                source="auto_learner"
            ))

        # 2. Append text to background LLM processing buffer
        async with self._buffer_lock:
            self._message_buffer.append(f"User: {text}")

    async def _buffer_processing_loop(self) -> None:
        """Processes buffered logs every 60 seconds via VLM/LLM extractors."""
        while self._running:
            try:
                await asyncio.sleep(60.0)
                
                snippet = ""
                async with self._buffer_lock:
                    if len(self._message_buffer) >= 4:  # Process when we have 4+ turns
                        snippet = "\n".join(self._message_buffer)
                        self._message_buffer.clear()

                if snippet and self._llm_extractor:
                    facts = await self._llm_extractor.extract_facts(snippet)
                    for fact in facts:
                        fact_type = fact.get("type", "memory")
                        content = fact.get("fact", "").strip()
                        if content:
                            is_new = await self._save_fact(fact_type, content, 0.8, "llm_extractor")
                            if is_new:
                                await self._bus.publish(Event(
                                    type=EventType.FACT_LEARNED,
                                    data={"type": fact_type, "fact": content},
                                    source="auto_learner"
                                ))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in AutoLearner processing loop: {exc}")
        logger.debug("AutoLearner buffer loop terminated.")
