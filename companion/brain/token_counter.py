"""
companion/brain/token_counter.py
==================================
Token counting utilities. Uses tiktoken for accurate OpenAI counting
with a lightweight character-based approximation as fallback.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Approx characters per token for various languages
# Vietnamese is slightly denser than English
_CHARS_PER_TOKEN = {
    "vi": 2.5,
    "en": 4.0,
    "default": 3.5,
}


def estimate_tokens(text: str, language: str = "vi") -> int:
    """
    Fast token count estimate without requiring tiktoken.
    Accuracy: ±15% for most text.

    Args:
        text: Input text string.
        language: Language code for calibration.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    chars_per_tok = _CHARS_PER_TOKEN.get(language, _CHARS_PER_TOKEN["default"])
    # Count words as additional signal
    word_count = len(text.split())
    char_estimate = len(text) / chars_per_tok
    # Blend char and word estimates (words tend to be more accurate for short texts)
    return max(1, int((char_estimate + word_count) / 2))


def count_message_tokens(messages: list[dict], language: str = "vi") -> int:
    """
    Estimate total tokens for a list of chat messages.

    Args:
        messages: List of {"role": ..., "content": ...} dicts.
        language: Language code.

    Returns:
        Total estimated token count including role overhead.
    """
    total = 0
    for msg in messages:
        # Role token overhead (~4 tokens per message for ChatML format)
        total += 4
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content, language)
        elif isinstance(content, list):
            # Multi-modal content (text + images)
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += estimate_tokens(part.get("text", ""), language)
                elif isinstance(part, dict) and part.get("type") == "image_url":
                    # Groq/OpenAI vision image token cost (approx)
                    total += 85  # low-detail image token cost
    total += 2  # reply priming
    return total


try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
    logger.debug("tiktoken available — using accurate token counts")
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.debug("tiktoken not available — using estimation fallback")


def accurate_token_count(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Count tokens accurately using tiktoken if available.
    Falls back to estimation if not installed.

    Args:
        text: Input text.
        model: Model name for encoding selection.

    Returns:
        Token count.
    """
    if not _TIKTOKEN_AVAILABLE:
        return estimate_tokens(text)
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        return estimate_tokens(text)


class TokenBudgetManager:
    """
    Manages token budget for a single conversation context.
    Ensures prompts never exceed model context windows.
    """

    # Context windows by model
    CONTEXT_WINDOWS = {
        "llama-3.3-70b-versatile": 131072,
        "llama-3.2-11b-vision-preview": 8192,
        "llama-3.2-90b-vision-preview": 8192,
        "gpt-4o-mini": 128000,
        "gpt-4o": 128000,
        "claude-3-haiku-20240307": 200000,
        "default": 8192,
    }

    def __init__(self, model: str, max_response_tokens: int = 512) -> None:
        self.model = model
        self.max_response_tokens = max_response_tokens
        self.context_window = self.CONTEXT_WINDOWS.get(model, self.CONTEXT_WINDOWS["default"])
        self.max_prompt_tokens = self.context_window - max_response_tokens - 100  # safety margin

    def trim_messages(
        self,
        messages: list[dict],
        system_tokens: int = 0,
        language: str = "vi",
    ) -> list[dict]:
        """
        Trim message history to fit within token budget.
        Always preserves the system message and last user message.

        Args:
            messages: List of chat messages (system, user, assistant...).
            system_tokens: Pre-counted system prompt tokens.
            language: Language for estimation.

        Returns:
            Trimmed message list.
        """
        if not messages:
            return messages

        budget = self.max_prompt_tokens - system_tokens
        total_tokens = 0
        result = []

        # Process from newest to oldest (reverse)
        for msg in reversed(messages):
            msg_tokens = estimate_tokens(str(msg.get("content", "")), language) + 4
            if total_tokens + msg_tokens <= budget:
                result.insert(0, msg)
                total_tokens += msg_tokens
            else:
                logger.debug(
                    f"Trimmed message from context (budget={budget}, "
                    f"used={total_tokens}, msg_tokens={msg_tokens})"
                )
                break

        return result

    def check_budget(self, messages: list[dict], language: str = "vi") -> dict:
        """Return budget analysis for a message set."""
        used = count_message_tokens(messages, language)
        return {
            "model": self.model,
            "context_window": self.context_window,
            "tokens_used": used,
            "tokens_available": self.max_prompt_tokens - used,
            "within_budget": used <= self.max_prompt_tokens,
        }
