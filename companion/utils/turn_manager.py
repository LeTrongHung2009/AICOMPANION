"""
companion/utils/turn_manager.py
================================
Turn-taking lock manager. Implements an asyncio.Lock gate to ensure
voice output, text generation, and screen analysis never overlap.
This is the traffic control layer of MyCompanion.
"""

from __future__ import annotations

import asyncio
import time
import logging
from contextlib import asynccontextmanager
from enum import Enum
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class TurnState(Enum):
    """Current system turn state."""
    IDLE = "idle"
    USER_INPUT = "user_input"
    AI_THINKING = "ai_thinking"
    TTS_SPEAKING = "tts_speaking"
    VISION_PROCESSING = "vision_processing"
    STT_LISTENING = "stt_listening"
    DREAMING = "dreaming"


class TurnManager:
    """
    Centralized turn-taking controller using asyncio.Lock.

    Guarantees:
    - Only one "speaking" turn at a time.
    - User input can interrupt boredom/vision turns (not TTS).
    - Lock state is always observable for UI feedback.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state = TurnState.IDLE
        self._state_changed_at = time.monotonic()
        self._current_holder: Optional[str] = None
        self._total_turns: int = 0
        self._lock_acquisitions: dict[str, int] = {}

    @property
    def state(self) -> TurnState:
        return self._state

    @property
    def is_busy(self) -> bool:
        """True if the system is actively processing a turn."""
        return self._lock.locked()

    @property
    def current_holder(self) -> Optional[str]:
        return self._current_holder

    @property
    def time_in_current_state(self) -> float:
        return time.monotonic() - self._state_changed_at

    def _set_state(self, state: TurnState, holder: str) -> None:
        self._state = state
        self._current_holder = holder
        self._state_changed_at = time.monotonic()
        logger.debug(f"Turn state: {state.value} (holder: {holder})")

    @asynccontextmanager
    async def acquire_turn(
        self,
        state: TurnState,
        holder: str = "unknown",
        timeout: Optional[float] = None,
    ) -> AsyncGenerator[None, None]:
        """
        Context manager that acquires the turn lock.

        Args:
            state: The TurnState to set while holding the lock.
            holder: Name of the subsystem requesting the turn.
            timeout: Optional seconds to wait for the lock.

        Raises:
            asyncio.TimeoutError: If timeout expires without acquiring lock.
        """
        try:
            if timeout is not None:
                await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            else:
                await self._lock.acquire()

            self._set_state(state, holder)
            self._total_turns += 1
            self._lock_acquisitions[holder] = self._lock_acquisitions.get(holder, 0) + 1
            logger.debug(f"[TurnManager] Lock acquired by '{holder}' — state: {state.value}")
            yield

        finally:
            if self._lock.locked():
                self._lock.release()
            self._set_state(TurnState.IDLE, "")
            logger.debug(f"[TurnManager] Lock released by '{holder}'")

    async def try_acquire_turn(
        self,
        state: TurnState,
        holder: str = "unknown",
        timeout: float = 0.1,
    ) -> bool:
        """
        Non-blocking check whether the turn can be acquired.
        Returns True if immediately available, False if busy.
        """
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            self._set_state(state, holder)
            self._lock.release()
            return True
        except asyncio.TimeoutError:
            return False

    def stats(self) -> dict:
        """Return turn manager statistics."""
        return {
            "current_state": self._state.value,
            "current_holder": self._current_holder,
            "time_in_state_seconds": round(self.time_in_current_state, 2),
            "total_turns": self._total_turns,
            "acquisitions_by_holder": self._lock_acquisitions.copy(),
        }


# Global singleton
_turn_manager: Optional[TurnManager] = None


def get_turn_manager() -> TurnManager:
    """Get or create the global TurnManager instance."""
    global _turn_manager
    if _turn_manager is None:
        _turn_manager = TurnManager()
    return _turn_manager
