"""
companion/learning/llm_extractor.py
===================================
LLM Fact Extractor.
Invokes background AI Cortex calls to parse complex preferences,
dislikes, or life details that are implicit in chat.
"""

from __future__ import annotations

import logging
import json
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

class LLMExtractor:
    """
    Submits recent dialog history logs to AI Cortex extractor endpoints.
    """

    def __init__(self, extract_fn: Callable[[str], Awaitable[Optional[str]]]) -> None:
        """
        Args:
            extract_fn: Async callback to submit prompt payload to cortex.
        """
        self._extract_fn = extract_fn

    async def extract_facts(self, conversation_snippet: str) -> list[dict]:
        """
        Submit Snippet transcript to LLM parser.
        
        Returns:
            List of parsed fact dictionaries.
        """
        if not conversation_snippet:
            return []

        try:
            logger.debug("Calling background LLM fact extraction...")
            raw_response = await self._extract_fn(conversation_snippet)
            if raw_response:
                # Strip markdown syntax block wrapping
                cleaned = raw_response.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    logger.debug(f"LLM fact extraction parsed {len(parsed)} potential facts.")
                    return parsed
        except Exception as exc:
            logger.error(f"Failed to extract facts via LLM: {exc}")

        return []
