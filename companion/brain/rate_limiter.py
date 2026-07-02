"""
companion/brain/rate_limiter.py
================================
Token-bucket rate limiter and daily quota tracker for Cloud API calls.
Enforces Groq Free Tier limits: ~6000 TPM, 30 RPM, ~30k tokens/day.
"""

from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    Classic token-bucket algorithm for rate limiting.
    Refills at `refill_rate` tokens/second up to `capacity`.
    """
    capacity: float          # Max tokens in bucket
    refill_rate: float       # Tokens added per second
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False, default_factory=time.monotonic)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self._tokens = self.capacity

    async def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens. Returns True if successful, False if rate-limited.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def wait_for(self, tokens: float = 1.0) -> float:
        """
        Wait until enough tokens are available, then consume them.
        Returns the time waited in seconds.
        """
        start = time.monotonic()
        while True:
            if await self.consume(tokens):
                return time.monotonic() - start
            # Sleep until we'd have enough tokens
            async with self._lock:
                deficit = tokens - self._tokens
                wait_time = deficit / self.refill_rate
            await asyncio.sleep(max(0.05, wait_time * 0.9))

    @property
    def available(self) -> float:
        """Current available tokens (approximate, not thread-safe)."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        return min(self.capacity, self._tokens + elapsed * self.refill_rate)


class DailyQuotaTracker:
    """
    Tracks daily API token usage and enforces a hard quota cap.
    Persists state to JSON file so quota survives restarts.
    """

    def __init__(self, quota: int, persist_path: Optional[Path] = None) -> None:
        self.quota = quota
        self._persist_path = persist_path
        self._used_today: int = 0
        self._date_str: str = self._today()
        self._lock = asyncio.Lock()
        self._load()

    def _today(self) -> str:
        from datetime import date
        return date.today().isoformat()

    def _load(self) -> None:
        """Load persisted quota state."""
        if self._persist_path and self._persist_path.exists():
            try:
                data = json.loads(self._persist_path.read_text())
                if data.get("date") == self._today():
                    self._used_today = data.get("used", 0)
                    logger.info(f"Resumed daily quota: {self._used_today}/{self.quota} tokens used today")
            except Exception as exc:
                logger.warning(f"Could not load quota state: {exc}")

    def _save(self) -> None:
        """Persist quota state to disk."""
        if self._persist_path:
            try:
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)
                self._persist_path.write_text(
                    json.dumps({"date": self._today(), "used": self._used_today})
                )
            except Exception as exc:
                logger.warning(f"Could not save quota state: {exc}")

    async def check_and_consume(self, tokens: int) -> bool:
        """
        Check if tokens can be consumed without exceeding daily quota.
        Returns False if quota would be exceeded.
        """
        async with self._lock:
            # Reset on new day
            today = self._today()
            if today != self._date_str:
                self._used_today = 0
                self._date_str = today
                logger.info("Daily token quota reset for new day.")

            if self._used_today + tokens > self.quota:
                remaining = self.quota - self._used_today
                logger.warning(
                    f"Daily quota check: would use {tokens} tokens but only "
                    f"{remaining} remain of {self.quota} daily limit."
                )
                return False

            self._used_today += tokens
            self._save()
            logger.debug(f"Quota consumed: {tokens} tokens. Daily total: {self._used_today}/{self.quota}")
            return True

    @property
    def remaining(self) -> int:
        """Tokens remaining for today."""
        return max(0, self.quota - self._used_today)

    @property
    def used(self) -> int:
        return self._used_today

    @property
    def percentage_used(self) -> float:
        return (self._used_today / self.quota) * 100 if self.quota > 0 else 0.0

    def stats(self) -> dict:
        return {
            "date": self._date_str,
            "used_tokens": self._used_today,
            "quota_tokens": self.quota,
            "remaining_tokens": self.remaining,
            "percentage_used": round(self.percentage_used, 1),
        }


class RateLimiter:
    """
    Composite rate limiter combining token-bucket (per-minute)
    and daily quota tracking. Used by all API clients.
    """

    def __init__(
        self,
        tokens_per_minute: int = 5500,
        requests_per_minute: int = 25,
        daily_token_quota: int = 28000,
        quota_persist_path: Optional[Path] = None,
    ) -> None:
        # Token-bucket for tokens/minute
        self._token_bucket = TokenBucket(
            capacity=float(tokens_per_minute),
            refill_rate=tokens_per_minute / 60.0,
        )
        # Token-bucket for requests/minute
        self._request_bucket = TokenBucket(
            capacity=float(requests_per_minute),
            refill_rate=requests_per_minute / 60.0,
        )
        self.daily_quota = DailyQuotaTracker(daily_token_quota, quota_persist_path)
        self._total_requests: int = 0
        self._blocked_requests: int = 0

    async def acquire(self, estimated_tokens: int = 100) -> bool:
        """
        Request permission to make an API call.

        Args:
            estimated_tokens: Estimated token count for this request.

        Returns:
            True if allowed, False if daily quota exceeded.
        """
        # Check daily quota first (hard limit)
        if not await self.daily_quota.check_and_consume(estimated_tokens):
            self._blocked_requests += 1
            return False

        # Wait for request-rate slot
        waited_req = await self._request_bucket.wait_for(1.0)
        if waited_req > 0.1:
            logger.debug(f"Request throttled: waited {waited_req:.2f}s for RPM slot")

        # Wait for token-rate slot
        waited_tok = await self._token_bucket.wait_for(min(estimated_tokens, 1000))
        if waited_tok > 0.1:
            logger.debug(f"Token throttled: waited {waited_tok:.2f}s for TPM slot")

        self._total_requests += 1
        return True

    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "blocked_requests": self._blocked_requests,
            "token_bucket_available": round(self._token_bucket.available, 1),
            "request_bucket_available": round(self._request_bucket.available, 1),
            "daily_quota": self.daily_quota.stats(),
        }
