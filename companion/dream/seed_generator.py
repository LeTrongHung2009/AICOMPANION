"""
companion/dream/seed_generator.py
=================================
Conversation Seed Generator.
Generates dialogue topics and prompts based on daily summaries
to prompt the user with interesting topics in subsequent sessions.
"""

from __future__ import annotations

import logging
import json
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

class SeedGenerator:
    """
    Formulates seed suggestions based on synthesized memories to steer tomorrow's starter.
    """

    def __init__(self, generate_fn: Callable[[str], Awaitable[Optional[str]]]) -> None:
        """
        Args:
            generate_fn: Async callback to run LLM requests.
        """
        self._generate_fn = generate_fn

    async def generate_tomorrow_seeds(self, daily_summary: str) -> list[str]:
        """
        Generates list of dialogue seed prompts.
        """
        if not daily_summary:
            return []

        prompt = (
            f"Dựa trên tóm tắt hoạt động hôm nay, hãy đề xuất 3 chủ đề trò chuyện "
            f"thú vị cho ngày mai để Hana bắt chuyện với chủ nhân. "
            f"Trả về danh sách định dạng JSON array ví dụ: [\"topic 1\", \"topic 2\"].\n\n"
            f"Tóm tắt: {daily_summary}"
        )

        try:
            resp = await self._generate_fn(prompt)
            if resp:
                # Clean block code syntax
                cleaned = resp.replace("```json", "").replace("```", "").strip()
                seeds = json.loads(cleaned)
                if isinstance(seeds, list):
                    logger.info(f"Generated {len(seeds)} conversation seeds for tomorrow.")
                    return [str(s) for s in seeds]
        except Exception as exc:
            logger.error(f"Failed to generate conversation seeds: {exc}")

        return []
