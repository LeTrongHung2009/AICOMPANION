"""
companion/brain/gemini_client.py
==================================
Google Gemini API client for multimodal tasks (vision + text).
Uses gemini-2.5-flash for fast, free vision analysis and deep reasoning.
Primary replacement for Groq vision and Anthropic fallback.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_VISION_MODEL = "gemini-2.5-flash"  # Updated to latest model
GEMINI_CHAT_MODEL = "gemini-2.5-flash"    # Updated to latest model

REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=45.0, write=10.0, pool=5.0)


class GeminiAPIError(Exception):
    """Gemini API specific errors."""
    def __init__(self, message: str, status_code: int = 0) -> None:
        super().__init__(message)
        self.status_code = status_code


class GeminiRateLimitError(GeminiAPIError):
    """Raised when Gemini returns 429 Too Many Requests."""
    pass


class GeminiClient:
    """
    Async Gemini API client for vision and chat tasks.
    
    Features:
    - Vision analysis with gemini-1.5-flash
    - Chat/text generation with gemini-1.5-flash
    - Automatic 429 handling
    """

    def __init__(
        self,
        api_key: str,
        vision_model: str = GEMINI_VISION_MODEL,
        chat_model: str = GEMINI_CHAT_MODEL,
        max_tokens: int = 512,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.vision_model = vision_model
        self.chat_model = chat_model
        self.max_tokens = max_tokens
        self._client: Optional[httpx.AsyncClient] = None
        self._total_requests: int = 0
        self._total_tokens_used: int = 0
        self._rate_limit_hits: int = 0

    def _get_headers(self) -> dict:
        return {"Content-Type": "application/json"}

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily initialize the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, http2=False)
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
        Send a chat completion request to Gemini.
        
        Args:
            messages: List of {\"role\": ..., \"content\": ...} dicts.
            temperature: Sampling temperature (0.0–1.0).
            max_tokens: Max response tokens. Uses class default if None.
            model_override: Override the default chat model.
        
        Returns:
            Response text string, or None on failure.
        """
        model = model_override or self.chat_model
        tokens = max_tokens or self.max_tokens
        
        # Convert OpenAI-style messages to Gemini format
        gemini_contents = []
        system_instruction = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content if isinstance(content, str) else ""
            elif role in ("user", "assistant"):
                gemini_contents.append({
                    "role": "user" if role == "user" else "model",
                    "parts": [{"text": content}] if isinstance(content, str) else content,
                })
        
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": min(1.0, temperature),
                "maxOutputTokens": tokens,
            },
        }
        
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        try:
            client = await self._ensure_client()
            endpoint = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={self.api_key}"
            
            resp = await client.post(endpoint, json=payload, headers=self._get_headers())
            self._total_requests += 1
            
            if resp.status_code == 429:
                self._rate_limit_hits += 1
                raise GeminiRateLimitError("Gemini rate limited", status_code=429)
            
            if resp.status_code != 200:
                body = resp.text[:200]
                raise GeminiAPIError(f"Gemini API error {resp.status_code}: {body}", status_code=resp.status_code)
            
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("Gemini returned no candidates")
                return None
            
            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts:
                return None
            
            text = content_parts[0].get("text", "")
            logger.debug(f"Gemini response: {len(text)} chars")
            return text.strip()
            
        except (GeminiRateLimitError, GeminiAPIError):
            raise
        except httpx.TimeoutException:
            logger.error("Gemini request timed out")
            return None
        except Exception as exc:
            logger.error(f"Gemini error: {exc}", exc_info=True)
            return None

    async def chat_with_image(
        self,
        text_prompt: str,
        image_bytes: bytes,
        system_prompt: str = "",
        temperature: float = 0.5,
    ) -> Optional[str]:
        """
        Send a vision request (image + text) to Gemini.
        
        Args:
            text_prompt: The question about the image.
            image_bytes: JPEG image bytes.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature.
        
        Returns:
            VLM response text, or None on failure.
        """
        import base64
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        contents = [{
            "role": "user",
            "parts": [
                {"text": text_prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": b64_image,
                    }
                },
            ],
        }]
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": min(1.0, temperature),
                "maxOutputTokens": 256,
            },
        }
        
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        
        try:
            client = await self._ensure_client()
            endpoint = f"{GEMINI_API_BASE}/models/{self.vision_model}:generateContent?key={self.api_key}"
            
            resp = await client.post(endpoint, json=payload, headers=self._get_headers())
            self._total_requests += 1
            
            if resp.status_code == 429:
                self._rate_limit_hits += 1
                raise GeminiRateLimitError("Gemini vision rate limited", status_code=429)
            
            if resp.status_code != 200:
                raise GeminiAPIError(f"Gemini vision error {resp.status_code}: {resp.text[:200]}")
            
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            
            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts:
                return None
            
            text = content_parts[0].get("text", "")
            logger.debug(f"Gemini vision response: {len(text)} chars")
            return text.strip()
            
        except (GeminiRateLimitError, GeminiAPIError):
            raise
        except httpx.TimeoutException:
            logger.error("Gemini vision request timed out")
            return None
        except Exception as exc:
            logger.error(f"Gemini vision error: {exc}", exc_info=True)
            return None

    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_tokens_used": self._total_tokens_used,
            "rate_limit_hits": self._rate_limit_hits,
        }
