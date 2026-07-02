"""
companion/brain/router.py
==========================
High-level AI router. Combines rate limiting, caching, fallback
management, and prompt building into a single chat() interface.
"""

from __future__ import annotations

import logging
from typing import Optional

from companion.brain.fallback_manager import FallbackManager, Provider
from companion.brain.rate_limiter import RateLimiter
from companion.brain.response_cache import ResponseCache
from companion.brain.token_counter import TokenBudgetManager, estimate_tokens
from companion.brain.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AIRouter:
    """
    The central AI routing layer.

    Flow for each request:
    1. Check rate limiter (daily quota + per-minute)
    2. Check response cache (hash-based)
    3. Build prompt with current context
    4. Try providers via FallbackManager
    5. Cache successful response
    6. Return text to caller
    """

    def __init__(
        self,
        fallback_manager: FallbackManager,
        rate_limiter: RateLimiter,
        response_cache: ResponseCache,
        prompt_builder: PromptBuilder,
        max_tokens: int = 512,
        language: str = "vi",
    ) -> None:
        self.fallback = fallback_manager
        self.rate_limiter = rate_limiter
        self.cache = response_cache
        self.prompt_builder = prompt_builder
        self.max_tokens = max_tokens
        self.language = language
        self._total_calls: int = 0
        self._cached_hits: int = 0
        self._rate_blocked: int = 0

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        cache_ttl: float = 3600.0,
    ) -> Optional[str]:
        """
        Execute a chat completion with full middleware stack.

        Args:
            messages: Complete chat message list (including system prompt).
            temperature: Sampling temperature.
            max_tokens: Override max token limit.
            use_cache: Whether to check/populate the response cache.
            cache_ttl: Cache TTL for this response.

        Returns:
            AI response text, or None if all providers failed.
        """
        self._total_calls += 1
        tokens = max_tokens or self.max_tokens

        # Estimate tokens for rate limiting
        estimated_input_tokens = estimate_tokens(
            " ".join(str(m.get("content", "")) for m in messages),
            self.language,
        )
        estimated_total = estimated_input_tokens + tokens

        # 1. Cache check
        if use_cache:
            primary_model = "llama-3.3-70b-versatile"  # Cache key uses primary model
            cached = await self.cache.get(messages, primary_model)
            if cached is not None:
                self._cached_hits += 1
                logger.debug("Returning cached AI response")
                return cached

        # 2. Rate limit check
        allowed = await self.rate_limiter.acquire(estimated_total)
        if not allowed:
            self._rate_blocked += 1
            logger.warning("Request blocked by rate limiter / daily quota")
            return self._quota_exceeded_response()

        # 3. Send to provider chain
        response, provider_used = await self.fallback.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=tokens,
        )

        # 4. Cache successful response
        if response and use_cache:
            primary_model = "llama-3.3-70b-versatile"
            await self.cache.set(messages, primary_model, response, ttl=cache_ttl)

        if response:
            logger.debug(f"AI response via {provider_used.value}: {len(response)} chars")

        return response

    def _quota_exceeded_response(self) -> str:
        """Friendly fallback when daily quota is exhausted."""
        return (
            "Ôi, mình đã dùng hết quota API cho hôm nay rồi! "
            "Chúng ta hãy tiếp tục nói chuyện vào ngày mai nhé? "
            "Mình vẫn ở đây với bạn đó! 🌙"
        )

    async def generate_with_context(
        self,
        user_message: str,
        conversation_history: list[dict],
        mood_state: Optional[dict] = None,
        screen_context: Optional[str] = None,
        user_facts: Optional[list[str]] = None,
        is_boredom: bool = False,
        temperature: float = 0.8,
    ) -> Optional[str]:
        """
        High-level chat that auto-builds the system prompt.

        Args:
            user_message: Current user input.
            conversation_history: Previous turns (user/assistant).
            mood_state: Current 3-tier mood state.
            screen_context: Screen VLM description.
            user_facts: Known facts about user.
            is_boredom: True if this is a boredom-initiated message.
            temperature: Sampling temperature.

        Returns:
            AI response text.
        """
        system_prompt = self.prompt_builder.build_system_prompt(
            mood_state=mood_state,
            screen_context=screen_context,
            user_facts=user_facts,
            conversation_count=len(conversation_history),
            is_boredom_mode=is_boredom,
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-20:])  # Keep last 20 turns
        messages.append({"role": "user", "content": user_message})

        return await self.chat(
            messages=messages,
            temperature=temperature,
            use_cache=not is_boredom,  # Don't cache boredom responses
        )

    def stats(self) -> dict:
        return {
            "total_calls": self._total_calls,
            "cached_hits": self._cached_hits,
            "rate_blocked": self._rate_blocked,
            "cache_stats": self.cache.stats(),
            "rate_limiter_stats": self.rate_limiter.stats(),
            "fallback_stats": self.fallback.stats(),
        }
