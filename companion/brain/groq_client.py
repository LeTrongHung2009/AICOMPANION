"""
companion/brain/groq_client.py
================================
Groq API client for text generation (Llama 3.3) and vision (Llama 3.2 Vision).
Uses httpx for fully async HTTP. Handles 429 rate-limit responses gracefully.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_CHAT_ENDPOINT = f"{GROQ_API_BASE}/chat/completions"
GROQ_AUDIO_ENDPOINT = f"{GROQ_API_BASE}/audio/transcriptions"

# Request timeout settings
REQUEST_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=45.0,
    write=10.0,
    pool=5.0,
)


class GroqAPIError(Exception):
    """Groq API specific errors."""
    def __init__(self, message: str, status_code: int = 0, retry_after: float = 0) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class GroqRateLimitError(GroqAPIError):
    """Raised when Groq returns 429 Too Many Requests."""
    pass


class GroqClient:
    """
    Async Groq API client.

    Features:
    - Text chat with Llama 3.3 70B Versatile
    - Vision chat with Llama 3.2 11B Vision
    - Audio transcription with Whisper large-v3
    - Automatic 429 handling with retry-after
    """

    def __init__(
        self,
        api_key: str,
        chat_model: str = "llama-3.3-70b-versatile",
        vision_model: str = "llama-3.2-11b-vision-preview",
        whisper_model: str = "whisper-large-v3",
        max_tokens: int = 512,
    ) -> None:
        if not api_key:
            raise ValueError("Groq API key is required")
        self.api_key = api_key
        self.chat_model = chat_model
        self.vision_model = vision_model
        self.whisper_model = whisper_model
        self.max_tokens = max_tokens
        self._client: Optional[httpx.AsyncClient] = None
        self._total_requests: int = 0
        self._total_tokens_used: int = 0
        self._rate_limit_hits: int = 0

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily initialize the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                http2=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
        model_override: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send a chat completion request to Groq.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            temperature: Sampling temperature (0.0–2.0).
            max_tokens: Max response tokens. Uses class default if None.
            model_override: Override the default chat model.

        Returns:
            Response text string, or None on failure.

        Raises:
            GroqRateLimitError: On 429 responses.
        """
        model = model_override or self.chat_model
        tokens = max_tokens or self.max_tokens
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": tokens,
            "stream": False,
        }

        try:
            client = await self._ensure_client()
            resp = await client.post(
                GROQ_CHAT_ENDPOINT,
                json=payload,
                headers=self._get_headers(),
            )
            self._total_requests += 1

            if resp.status_code == 429:
                self._rate_limit_hits += 1
                retry_after = float(resp.headers.get("retry-after", "60"))
                raise GroqRateLimitError(
                    f"Groq rate limited (429). Retry after {retry_after}s",
                    status_code=429,
                    retry_after=retry_after,
                )

            if resp.status_code != 200:
                body = resp.text[:200]
                raise GroqAPIError(
                    f"Groq API error {resp.status_code}: {body}",
                    status_code=resp.status_code,
                )

            data = resp.json()
            usage = data.get("usage", {})
            self._total_tokens_used += usage.get("total_tokens", 0)

            content = data["choices"][0]["message"]["content"]
            logger.debug(
                f"Groq response: {len(content)} chars, "
                f"{usage.get('total_tokens', '?')} tokens"
            )
            return content

        except (GroqRateLimitError, GroqAPIError):
            raise
        except httpx.TimeoutException:
            logger.error("Groq request timed out")
            return None
        except httpx.RequestError as exc:
            logger.error(f"Groq request error: {exc}")
            return None
        except (KeyError, IndexError) as exc:
            logger.error(f"Groq response parse error: {exc}")
            return None

    async def chat_with_image(
        self,
        text_prompt: str,
        image_bytes: bytes,
        system_prompt: str = "",
        temperature: float = 0.5,
    ) -> Optional[str]:
        """
        Send a vision request (image + text) to Groq Llama Vision.

        Args:
            text_prompt: The question about the image.
            image_bytes: JPEG image bytes.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature.

        Returns:
            VLM response text, or None on failure.
        """
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}",
                        "detail": "low",  # Use low detail to save tokens
                    },
                },
                {"type": "text", "text": text_prompt},
            ],
        })

        return await self.chat(
            messages=messages,
            temperature=temperature,
            model_override=self.vision_model,
            max_tokens=256,  # Shorter for screen descriptions
        )

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str = "vi",
    ) -> Optional[str]:
        """
        Transcribe audio via Groq Whisper large-v3.

        Args:
            audio_bytes: WAV audio bytes.
            filename: Filename hint for the API.
            language: Language code (ISO 639-1).

        Returns:
            Transcription text, or None on failure.
        """
        try:
            client = await self._ensure_client()
            files = {"file": (filename, audio_bytes, "audio/wav")}
            data = {
                "model": self.whisper_model,
                "response_format": "text",
                "language": language,
            }
            headers = {"Authorization": f"Bearer {self.api_key}"}

            resp = await client.post(
                GROQ_AUDIO_ENDPOINT,
                files=files,
                data=data,
                headers=headers,
            )
            self._total_requests += 1

            if resp.status_code == 429:
                self._rate_limit_hits += 1
                raise GroqRateLimitError("Whisper rate limited", status_code=429, retry_after=60)

            if resp.status_code != 200:
                raise GroqAPIError(f"Whisper error {resp.status_code}: {resp.text[:200]}")

            text = resp.text.strip()
            logger.debug(f"Whisper transcription: '{text[:80]}…'" if len(text) > 80 else f"Whisper: '{text}'")
            return text if text else None

        except (GroqRateLimitError, GroqAPIError):
            raise
        except httpx.TimeoutException:
            logger.error("Whisper request timed out")
            return None
        except Exception as exc:
            logger.error(f"Whisper error: {exc}", exc_info=True)
            return None

    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_tokens_used": self._total_tokens_used,
            "rate_limit_hits": self._rate_limit_hits,
        }
