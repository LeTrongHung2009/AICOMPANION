"""
companion/utils/event_bus.py
============================
Internal pub/sub event bus for decoupled inter-module communication.
Modules publish events; subscribers receive them via async callbacks.
This avoids tight coupling between the brain, UI, and peripheral systems.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """All system event types."""
    # Input events
    USER_TEXT_INPUT = auto()
    USER_VOICE_INPUT = auto()
    SCREEN_CONTEXT_UPDATED = auto()
    MICROPHONE_SILENCE = auto()

    # AI events
    AI_RESPONSE_READY = auto()
    AI_RESPONSE_CHUNK = auto()
    AI_ERROR = auto()
    AI_RATE_LIMITED = auto()

    # Output events
    TTS_START = auto()
    TTS_END = auto()
    TTS_ERROR = auto()

    # VTS events
    VTS_CONNECTED = auto()
    VTS_DISCONNECTED = auto()
    VTS_EXPRESSION_SET = auto()

    # Memory events
    FACT_LEARNED = auto()
    MEMORY_CONSOLIDATED = auto()
    PREFERENCE_UPDATED = auto()

    # Persona events
    MOOD_CHANGED = auto()
    BOREDOM_TRIGGERED = auto()
    DREAM_STARTED = auto()
    DREAM_ENDED = auto()

    # System events
    SYSTEM_STARTUP = auto()
    SYSTEM_SHUTDOWN = auto()
    IDLE_STATE_CHANGED = auto()
    ERROR_CRITICAL = auto()


@dataclass
class Event:
    """An event published to the event bus."""
    type: EventType
    data: Any = None
    source: str = "unknown"
    timestamp: float = field(default_factory=time.monotonic)
    metadata: dict = field(default_factory=dict)


# Callback type: async callable receiving an Event
AsyncCallback = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Lightweight async pub/sub event bus.

    Usage:
        bus = get_event_bus()
        bus.subscribe(EventType.AI_RESPONSE_READY, my_handler)
        await bus.publish(Event(EventType.AI_RESPONSE_READY, data="Hello!"))
    """

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[AsyncCallback]] = defaultdict(list)
        self._event_counts: dict[EventType, int] = defaultdict(int)
        self._total_events: int = 0
        self._error_count: int = 0

    def subscribe(self, event_type: EventType, callback: AsyncCallback) -> None:
        """
        Register a callback for an event type.

        Args:
            event_type: The event to subscribe to.
            callback: Async callable to invoke on event.
        """
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.name}: {callback.__qualname__}")

    def unsubscribe(self, event_type: EventType, callback: AsyncCallback) -> bool:
        """
        Remove a subscription. Returns True if removed.
        """
        subscribers = self._subscribers.get(event_type, [])
        if callback in subscribers:
            subscribers.remove(callback)
            logger.debug(f"Unsubscribed from {event_type.name}: {callback.__qualname__}")
            return True
        return False

    async def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish.

        Returns:
            Number of subscribers notified.
        """
        self._total_events += 1
        self._event_counts[event.type] += 1

        subscribers = self._subscribers.get(event.type, [])
        if not subscribers:
            logger.debug(f"Event {event.type.name} has no subscribers.")
            return 0

        tasks = [asyncio.create_task(self._safe_call(cb, event)) for cb in subscribers]
        await asyncio.gather(*tasks, return_exceptions=True)
        return len(tasks)

    async def _safe_call(self, callback: AsyncCallback, event: Event) -> None:
        """Invoke a callback, catching and logging any exceptions."""
        try:
            await callback(event)
        except Exception as exc:
            self._error_count += 1
            logger.error(
                f"EventBus error in subscriber {callback.__qualname__} "
                f"for event {event.type.name}: {exc}",
                exc_info=True,
            )

    def emit_sync(self, event: Event) -> None:
        """
        Schedule event publication on the running event loop.
        Safe to call from synchronous code (e.g., PyQt6 slots).
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.publish(event))
            else:
                logger.warning(f"Cannot emit {event.type.name} — no running event loop")
        except RuntimeError:
            logger.warning(f"Cannot emit {event.type.name} — RuntimeError")

    def stats(self) -> dict:
        """Return event bus statistics."""
        return {
            "total_events": self._total_events,
            "error_count": self._error_count,
            "subscriber_counts": {k.name: len(v) for k, v in self._subscribers.items() if v},
            "event_counts": {k.name: v for k, v in self._event_counts.items() if v > 0},
        }


# Global singleton
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global EventBus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
