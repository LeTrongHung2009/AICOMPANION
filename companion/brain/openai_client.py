"""
companion/brain/openai_client.py
==================================
OpenAI API client used as fallback when Groq is rate-limited.
Targets gpt-4o-mini for cost efficiency on free/low-cost tiers.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_CHAT_ENDPOINT = f"{OPENAI_API_BASE}/chat/completions"

REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)


class OpenAIAPIError(Exception):
    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAIRateLimitError(OpenAIAPIError):
    pass


class OpenAIClient:
    """
    Async OpenAI API client for chat completions.
    Used as fallback provider when Groq Free Tier is exhausted.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 512,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self._client: Optional[httpx.AsyncClient] = None
        self._total_requests: int = 0
        self._rate_limit_hits: int = 0

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, http2=True)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """
        Send a chat completion to OpenAI.

        Args:
            messages: Chat message list.
            temperature: Sampling temperature.
            max_tokens: Response token limit.

        Returns:
            Response text or None on failure.

        Raises:
            OpenAIRateLimitError: On 429 responses.
        """
        tokens = max_tokens or self.max_tokens
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": tokens,
        }

        try:
            client = await self._ensure_client()
            resp = await client.post(
                OPENAI_CHAT_ENDPOINT,
                json=payload,
                headers=self._headers(),
            )
            self._total_requests += 1

            if resp.status_code == 429:
                self._rate_limit_hits += 1
                raise OpenAIRateLimitError("OpenAI rate limited", status_code=429)

            if resp.status_code != 200:
                raise OpenAIAPIError(
                    f"OpenAI error {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.debug(f"OpenAI response: {len(content)} chars")
            return content

        except (OpenAIRateLimitError, OpenAIAPIError):
            raise
        except httpx.TimeoutException:
            logger.error("OpenAI request timed out")
            return None
        except Exception as exc:
            logger.error(f"OpenAI error: {exc}", exc_info=True)
            return None

    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "rate_limit_hits": self._rate_limit_hits,
        }
