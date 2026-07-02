"""
companion/brain/anthropic_client.py
=====================================
Anthropic Claude API client — second fallback in the provider chain.
Uses claude-3-haiku for fastest, cheapest inference.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_MESSAGES_ENDPOINT = f"{ANTHROPIC_API_BASE}/messages"
ANTHROPIC_API_VERSION = "2023-06-01"

REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)


class AnthropicAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


class AnthropicRateLimitError(AnthropicAPIError):
    pass


class AnthropicClient:
    """
    Async Anthropic API client for Claude messages.
    Second fallback provider, used when both Groq and OpenAI are unavailable.
    Converts OpenAI-style message format to Anthropic's system/messages format.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
        max_tokens: int = 512,
    ) -> None:
        if not api_key:
            raise ValueError("Anthropic API key is required")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self._client: Optional[httpx.AsyncClient] = None
        self._total_requests: int = 0
        self._rate_limit_hits: int = 0

    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "Content-Type": "application/json",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, http2=True)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """
        Convert OpenAI-style messages to Anthropic format.
        Extracts system message separately (Anthropic API requirement).

        Returns:
            Tuple of (system_prompt, anthropic_messages).
        """
        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content if isinstance(content, str) else ""
            elif role in ("user", "assistant"):
                anthropic_messages.append({
                    "role": role,
                    "content": content if isinstance(content, str) else str(content),
                })

        return system_prompt, anthropic_messages

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Send a messages request to Anthropic Claude.

        Args:
            messages: OpenAI-compatible message list (auto-converted).
            temperature: Sampling temperature (0.0–1.0 for Anthropic).
            max_tokens: Response token limit.

        Returns:
            Response text or None on failure.
        """
        tokens = max_tokens or self.max_tokens
        system_prompt, anthropic_messages = self._convert_messages(messages)

        if not anthropic_messages:
            logger.warning("No valid messages to send to Anthropic")
            return None

        payload: dict = {
            "model": self.model,
            "max_tokens": tokens,
            "temperature": min(1.0, temperature),  # Anthropic caps at 1.0
            "messages": anthropic_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            client = await self._ensure_client()
            resp = await client.post(
                ANTHROPIC_MESSAGES_ENDPOINT,
                json=payload,
                headers=self._headers(),
            )
            self._total_requests += 1

            if resp.status_code == 429:
                self._rate_limit_hits += 1
                raise AnthropicRateLimitError("Anthropic rate limited", status_code=429)

            if resp.status_code != 200:
                raise AnthropicAPIError(
                    f"Anthropic error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            content_blocks = data.get("content", [])
            if not content_blocks:
                logger.warning("Anthropic returned empty content")
                return None

            # Extract first text block
            text = next(
                (block["text"] for block in content_blocks if block.get("type") == "text"),
                None,
            )
            if text:
                logger.debug(f"Anthropic response: {len(text)} chars")
            return text

        except (AnthropicRateLimitError, AnthropicAPIError):
            raise
        except httpx.TimeoutException:
            logger.error("Anthropic request timed out")
            return None
        except Exception as exc:
            logger.error(f"Anthropic error: {exc}", exc_info=True)
            return None

    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "rate_limit_hits": self._rate_limit_hits,
        }
