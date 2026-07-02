"""
companion/dream/memory_synthesizer.py
=====================================
Memory Synthesizer.
Takes daily log scripts, invokes AI Cortex synthesis,
and saves summarized long-term vector/fact rows to SQLite.
"""

from __future__ import annotations

import logging
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

class MemorySynthesizer:
    """
    Interfaces with AICortex system prompts to extract high-level summary logs.
    Creates long-term facts in memory.
    """

    def __init__(
        self, 
        synthesis_fn: Callable[[str], Awaitable[Optional[str]]],
        save_fact_fn: Callable[[str, str, float, str], Awaitable[bool]]
    ) -> None:
        """
        Args:
            synthesis_fn: Async callable that takes log_text and returns summarized string.
            save_fact_fn: Async callback to register a fact (fact_type, content, confidence, source).
        """
        self._synthesis_fn = synthesis_fn
        self._save_fact = save_fact_fn

    async def consolidate_day(self, compressed_logs: str) -> Optional[str]:
        """
        Runs the async consolidation process.
        
        Returns:
            A summarized string block, or None.
        """
        if not compressed_logs or "No interactions" in compressed_logs:
            return None

        try:
            logger.info("Executing Memory consolidation via VLM/LLM...")
            summary = await self._synthesis_fn(compressed_logs)
            
            if summary:
                # Save as a long-term 'memory' fact
                await self._save_fact("memory", summary, 0.9, "dream_engine")
                logger.info("Consolidated daily logs saved into memory store.")
                return summary
        except Exception as exc:
            logger.error(f"Failed to consolidate day: {exc}")
        
        return None
