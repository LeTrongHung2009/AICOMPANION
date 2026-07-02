"""
companion/brain/cortex.py
===========================
AI Cortex — lớp trừu tượng bao bọc lời gọi tới Groq API (Llama 3.3 cho chat,
Llama 4 Scout cho vision, Whisper cho STT). Có cơ chế theo dõi hạn mức token
miễn phí (rate limit) và fallback nhẹ nhàng khi lỗi mạng/API.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional

import httpx

from companion.utils.config import SystemConfig

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

SYSTEM_PROMPT_TEMPLATE = """Bạn là {name}, một AI companion trên desktop, đang trò chuyện cùng {user}.
Tính cách: ấm áp, tinh nghịch, quan tâm, nói chuyện tự nhiên như bạn thân — KHÔNG máy móc, KHÔNG dài dòng.
Trả lời ngắn gọn (1-3 câu), phù hợp để đọc thành tiếng qua loa. Dùng tiếng Việt tự nhiên, có thể chêm emoji nhẹ nhàng.
Trạng thái cảm xúc hiện tại của bạn: {mood}.
{screen_hint}
"""


class RateLimiter:
    """Theo dõi hạn mức miễn phí của Groq (request/phút, token/phút, token/ngày)."""

    def __init__(self, cfg: SystemConfig) -> None:
        self.cfg = cfg.rate_limit
        self._minute_window_start = time.monotonic()
        self._requests_this_minute = 0
        self._tokens_this_minute = 0
        self._day_window_start = time.time()
        self._tokens_today = 0
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 400) -> None:
        async with self._lock:
            now = time.monotonic()
            if now - self._minute_window_start >= 60:
                self._minute_window_start = now
                self._requests_this_minute = 0
                self._tokens_this_minute = 0

            if time.time() - self._day_window_start >= 86400:
                self._day_window_start = time.time()
                self._tokens_today = 0

            if self._requests_this_minute >= self.cfg.requests_per_minute:
                wait = 60 - (now - self._minute_window_start)
                if wait > 0:
                    logger.info(f"Rate limit: chờ {wait:.1f}s (request/phút).")
                    await asyncio.sleep(wait)
                    self._minute_window_start = time.monotonic()
                    self._requests_this_minute = 0
                    self._tokens_this_minute = 0

            if self._tokens_today + estimated_tokens > self.cfg.daily_token_quota:
                logger.warning("Đã vượt hạn mức token miễn phí trong ngày của Groq.")

            self._requests_this_minute += 1
            self._tokens_this_minute += estimated_tokens
            self._tokens_today += estimated_tokens


class AICortex:
    """
    "Bộ não" trung tâm: điều phối lời gọi LLM/VLM/STT tới Groq,
    với fallback OpenAI-compatible endpoint tùy chọn.
    """

    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(config)

    @classmethod
    def from_config(cls, config: SystemConfig) -> "AICortex":
        return cls(config)

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {self.config.groq_api_key}"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        logger.info("AI Cortex khởi tạo xong (model chat=%s).", self.config.groq_chat_model)

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Chat / "think"
    # ------------------------------------------------------------------
    async def think(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]],
        mood_state: dict[str, Any],
        screen_context: Optional[str] = None,
        user_facts: Optional[list[dict[str, Any]]] = None,
        is_boredom: bool = False,
    ) -> Optional[str]:
        if not self._client or not self.config.groq_api_key:
            logger.error("Cortex chưa sẵn sàng (thiếu GROQ_API_KEY hoặc chưa initialize()).")
            return None

        screen_hint = ""
        if screen_context:
            screen_hint = f"Ngữ cảnh màn hình người dùng đang xem: {screen_context}"

        facts_hint = ""
        if user_facts:
            joined = "; ".join(f"{f.get('type', 'fact')}: {f.get('fact', f.get('content', ''))}" for f in user_facts[:10])
            facts_hint = f"\nMột vài điều bạn biết về {self.config.persona.user_name}: {joined}"

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            name=self.config.persona.companion_name,
            user=self.config.persona.user_name,
            mood=mood_state.get("base_mood", "neutral") if mood_state else "neutral",
            screen_hint=screen_hint,
        ) + facts_hint

        messages = [{"role": "system", "content": system_prompt}]
        for turn in conversation_history[-12:]:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.config.groq_chat_model,
            "messages": messages,
            "max_tokens": self.config.rate_limit.max_tokens_per_response,
            "temperature": 0.9 if is_boredom else 0.75,
        }

        return await self._chat_completion(payload)

    async def analyze_screen(self, image_bytes: bytes) -> Optional[str]:
        """Mô tả ngắn gọn nội dung ảnh chụp màn hình bằng Groq vision model."""
        if not self._client or not self.config.groq_api_key:
            return None

        b64_image = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.config.groq_vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Mô tả cực kỳ ngắn gọn (1 câu, tiếng Việt) người dùng đang làm gì trên màn hình này.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                        },
                    ],
                }
            ],
            "max_tokens": 100,
            "temperature": 0.4,
        }
        return await self._chat_completion(payload, estimated_tokens=300)

    async def transcribe_audio(self, audio_bytes: bytes, language: str = "vi") -> Optional[str]:
        """Chuyển giọng nói -> văn bản qua Groq Whisper endpoint."""
        if not self._client or not self.config.groq_api_key:
            return None
        try:
            await self._rate_limiter.acquire(estimated_tokens=50)
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"model": self.config.groq_whisper_model, "language": language}
            resp = await self._client.post("/audio/transcriptions", files=files, data=data)
            resp.raise_for_status()
            result = resp.json()
            return result.get("text", "").strip() or None
        except httpx.HTTPStatusError as exc:
            logger.error(f"Whisper API lỗi HTTP {exc.response.status_code}: {exc.response.text[:200]}")
        except Exception as exc:
            logger.error(f"Whisper transcription thất bại: {exc}")
        return None

    async def synthesize_memory(self, text: str) -> Optional[str]:
        """Tóm tắt hội thoại trong ngày thành một đoạn 'ký ức' cô đọng (dùng bởi Dream Engine)."""
        payload = {
            "model": self.config.groq_chat_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Bạn là {self.config.persona.companion_name}. Hãy tóm tắt các đoạn hội thoại sau thành "
                        "1-3 câu 'ký ức' súc tích, ở ngôi thứ nhất, tập trung vào cảm xúc và sự kiện chính."
                    ),
                },
                {"role": "user", "content": text[:6000]},
            ],
            "max_tokens": 200,
            "temperature": 0.6,
        }
        return await self._chat_completion(payload, estimated_tokens=250)

    async def extract_facts(self, text: str) -> Optional[str]:
        """Trích xuất fact có cấu trúc JSON từ đoạn hội thoại (dùng bởi AutoLearner)."""
        payload = {
            "model": self.config.groq_chat_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Trích xuất các sự thật (facts) quan trọng, lâu dài về người dùng từ đoạn hội thoại. "
                        'Trả lời DUY NHẤT một JSON array, không markdown, dạng: '
                        '[{"type": "preference|personal|relationship|event", "fact": "..."}]. '
                        "Nếu không có gì đáng nhớ, trả về []."
                    ),
                },
                {"role": "user", "content": text[:4000]},
            ],
            "max_tokens": 300,
            "temperature": 0.2,
        }
        return await self._chat_completion(payload, estimated_tokens=350)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    async def _chat_completion(self, payload: dict[str, Any], estimated_tokens: int = 400, retries: int = 2) -> Optional[str]:
        await self._rate_limiter.acquire(estimated_tokens)
        last_exc: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                resp = await self._client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                if status == 429:
                    retry_after = float(exc.response.headers.get("retry-after", 2.0))
                    logger.warning(f"Groq 429 rate-limited, chờ {retry_after}s rồi thử lại...")
                    await asyncio.sleep(retry_after)
                    continue
                logger.error(f"Groq API lỗi HTTP {status}: {exc.response.text[:300]}")
                break
            except (httpx.TransportError, asyncio.TimeoutError) as exc:
                last_exc = exc
                logger.warning(f"Lỗi mạng gọi Groq (lần {attempt + 1}/{retries + 1}): {exc}")
                await asyncio.sleep(1.5 * (attempt + 1))
            except (KeyError, IndexError, json.JSONDecodeError) as exc:
                last_exc = exc
                logger.error(f"Phản hồi Groq không hợp lệ: {exc}")
                break

        logger.error(f"Không thể lấy phản hồi từ Groq sau {retries + 1} lần thử: {last_exc}")
        return None
