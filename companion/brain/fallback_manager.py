"""
companion/brain/fallback_manager.py
=====================================
Manages the provider fallback chain: Groq → OpenAI → Anthropic.
Automatically switches providers on rate-limit errors and tracks
per-provider health for intelligent routing decisions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Optional

from companion.brain.groq_client import GroqClient, GroqRateLimitError, GroqAPIError
from companion.brain.openai_client import OpenAIClient, OpenAIRateLimitError, OpenAIAPIError
from companion.brain.anthropic_client import AnthropicClient, AnthropicRateLimitError, AnthropicAPIError

logger = logging.getLogger(__name__)


class Provider(Enum):
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NONE = "none"


class ProviderHealth:
    """Tracks the health and cooldown state of a single provider."""

    def __init__(self, name: str, cooldown_base: float = 60.0) -> None:
        self.name = name
        self.cooldown_base = cooldown_base
        self.is_available: bool = True
        self.unavailable_until: float = 0.0
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_used: float = 0.0

    def mark_success(self) -> None:
        self.is_available = True
        self.success_count += 1
        self.failure_count = max(0, self.failure_count - 1)
        self.last_used = time.monotonic()

    def mark_rate_limited(self, retry_after: float = 0.0) -> None:
        self.failure_count += 1
        cooldown = retry_after if retry_after > 0 else self.cooldown_base * (2 ** min(self.failure_count - 1, 4))
        self.unavailable_until = time.monotonic() + cooldown
        self.is_available = False
        logger.warning(f"Provider {self.name} rate-limited. Cooldown: {cooldown:.0f}s")

    def mark_error(self) -> None:
        self.failure_count += 1
        # Short cooldown on transient errors
        self.unavailable_until = time.monotonic() + 10.0

    def check_available(self) -> bool:
        if not self.is_available:
            if time.monotonic() >= self.unavailable_until:
                self.is_available = True
                logger.info(f"Provider {self.name} is available again")
        return self.is_available

    def to_dict(self) -> dict:
        return {
            "available": self.check_available(),
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "cooldown_remaining": max(0.0, round(self.unavailable_until - time.monotonic(), 1)),
        }


class FallbackManager:
    """
    Orchestrates the provider fallback chain.

    Chain: Groq → OpenAI → Anthropic → None (graceful degradation)

    On rate-limit: marks provider as cooling down, tries next.
    On API error: tries next provider immediately.
    On success: records provider health.
    """

    def __init__(
        self,
        groq: Optional[GroqClient] = None,
        openai: Optional[OpenAIClient] = None,
        anthropic: Optional[AnthropicClient] = None,
    ) -> None:
        self.groq = groq
        self.openai = openai
        self.anthropic = anthropic

        self._health = {
            Provider.GROQ: ProviderHealth("Groq"),
            Provider.OPENAI: ProviderHealth("OpenAI"),
            Provider.ANTHROPIC: ProviderHealth("Anthropic"),
        }
        self._active_provider = Provider.GROQ
        self._total_requests: int = 0
        self._successful_requests: int = 0

    def _get_provider_chain(self) -> list[Provider]:
        """Return available providers in priority order."""
        chain = []
        candidates = [Provider.GROQ, Provider.OPENAI, Provider.ANTHROPIC]
        for p in candidates:
            health = self._health[p]
            client = self._get_client(p)
            if client is not None and health.check_available():
                chain.append(p)
        return chain

    def _get_client(self, provider: Provider):
        """Get the client for a provider."""
        return {
            Provider.GROQ: self.groq,
            Provider.OPENAI: self.openai,
            Provider.ANTHROPIC: self.anthropic,
        }.get(provider)

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 512,
    ) -> tuple[Optional[str], Provider]:
        """
        Send a chat request through the provider fallback chain.

        Returns:
            Tuple of (response_text, provider_used).
            response_text is None if all providers failed.
        """
        self._total_requests += 1
        chain = self._get_provider_chain()

        if not chain:
            logger.error("No available providers in fallback chain!")
            return None, Provider.NONE

        for provider in chain:
            try:
                response = await self._send_to_provider(
                    provider, messages, temperature, max_tokens
                )
                if response:
                    self._health[provider].mark_success()
                    self._active_provider = provider
                    self._successful_requests += 1
                    logger.debug(f"Successfully used provider: {provider.value}")
                    return response, provider

            except (GroqRateLimitError,) as exc:
                self._health[provider].mark_rate_limited(
                    retry_after=getattr(exc, "retry_after", 60.0)
                )
                logger.warning(f"Groq rate-limited, falling back to next provider")
                continue

            except (OpenAIRateLimitError, AnthropicRateLimitError):
                self._health[provider].mark_rate_limited()
                logger.warning(f"{provider.value} rate-limited, falling back")
                continue

            except Exception as exc:
                self._health[provider].mark_error()
                logger.error(f"Provider {provider.value} error: {exc}", exc_info=True)
                continue

        logger.error("All providers in fallback chain failed")
        return None, Provider.NONE

    async def _send_to_provider(
        self,
        provider: Provider,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Dispatch to the appropriate provider client."""
        if provider == Provider.GROQ and self.groq:
            return await self.groq.chat(messages, temperature=temperature, max_tokens=max_tokens)
        elif provider == Provider.OPENAI and self.openai:
            return await self.openai.chat(messages, temperature=temperature, max_tokens=max_tokens)
        elif provider == Provider.ANTHROPIC and self.anthropic:
            return await self.anthropic.chat(messages, temperature=temperature, max_tokens=max_tokens)
        return None

    @property
    def active_provider(self) -> Provider:
        return self._active_provider

    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "active_provider": self._active_provider.value,
            "provider_health": {p.value: h.to_dict() for p, h in self._health.items()},
        }

    async def close_all(self) -> None:
        """Close all provider HTTP clients."""
        for client in [self.groq, self.openai, self.anthropic]:
            if client and hasattr(client, "close"):
                try:
                    await client.close()
                except Exception:
                    pass
