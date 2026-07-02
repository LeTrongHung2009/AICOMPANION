"""
companion/utils/priority_queue.py
==================================
Thread-safe async priority queue for message routing.
Implements the 4-tier priority system:
  P0 = User Text Input    (highest priority)
  P1 = Voice Interrupt
  P2 = Screen Event
  P3 = Boredom/Idle Init  (lowest priority)
"""

from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Message priority levels. Lower integer = higher priority."""
    USER_TEXT = 0    # Direct user text input
    VOICE = 1        # Voice/audio interrupt
    SCREEN = 2       # Screen context event
    BOREDOM = 3      # Idle boredom protocol


@dataclass(order=True)
class PrioritizedMessage:
    """
    A message with priority and timestamp for queue ordering.
    Ordered first by priority, then by insertion time (FIFO within tier).
    """
    priority: int
    timestamp: float = field(default_factory=time.monotonic)
    message: Any = field(default=None, compare=False)
    source: str = field(default="unknown", compare=False)
    metadata: dict = field(default_factory=dict, compare=False)

    @classmethod
    def create(
        cls,
        priority: Priority,
        message: Any,
        source: str = "unknown",
        metadata: Optional[dict] = None,
    ) -> "PrioritizedMessage":
        return cls(
            priority=int(priority),
            message=message,
            source=source,
            metadata=metadata or {},
        )


class AsyncPriorityQueue:
    """
    Async priority queue backed by asyncio.PriorityQueue.
    Provides typed access with Priority enum.
    """

    def __init__(self, maxsize: int = 100) -> None:
        self._queue: asyncio.PriorityQueue[PrioritizedMessage] = asyncio.PriorityQueue(maxsize=maxsize)
        self._put_count: dict[Priority, int] = {p: 0 for p in Priority}
        self._get_count: dict[Priority, int] = {p: 0 for p in Priority}

    async def put(
        self,
        priority: Priority,
        message: Any,
        source: str = "unknown",
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Put a message into the queue.

        Args:
            priority: Message priority tier.
            message: The message payload.
            source: Identifier of the sender.
            metadata: Optional metadata dictionary.
        """
        item = PrioritizedMessage.create(priority, message, source, metadata)
        await self._queue.put(item)
        self._put_count[priority] = self._put_count.get(priority, 0) + 1
        logger.debug(f"Queued [{Priority(priority).name}] from '{source}': {str(message)[:60]}")

    def put_nowait(
        self,
        priority: Priority,
        message: Any,
        source: str = "unknown",
        metadata: Optional[dict] = None,
    ) -> None:
        """Non-blocking put. Raises QueueFull if at capacity."""
        item = PrioritizedMessage.create(priority, message, source, metadata)
        self._queue.put_nowait(item)
        self._put_count[priority] = self._put_count.get(priority, 0) + 1

    async def get(self) -> PrioritizedMessage:
        """Get the highest-priority message, blocking until available."""
        item = await self._queue.get()
        self._get_count[item.priority] = self._get_count.get(item.priority, 0) + 1
        return item

    async def get_nowait(self) -> Optional[PrioritizedMessage]:
        """Non-blocking get. Returns None if queue is empty."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def task_done(self) -> None:
        """Mark the last gotten message as processed."""
        self._queue.task_done()

    def qsize(self) -> int:
        """Return current queue size."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Return True if queue is empty."""
        return self._queue.empty()

    def full(self) -> bool:
        """Return True if queue is full."""
        return self._queue.full()

    def stats(self) -> dict:
        """Return queue statistics."""
        return {
            "current_size": self.qsize(),
            "put_counts": {Priority(k).name: v for k, v in self._put_count.items()},
            "get_counts": {Priority(k).name: v for k, v in self._get_count.items()},
        }

    async def drain(self) -> list[PrioritizedMessage]:
        """Drain all current messages without blocking."""
        messages = []
        while not self._queue.empty():
            try:
                messages.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return messages

    def clear_priority(self, priority: Priority) -> int:
        """
        Remove all messages of a given priority.
        NOTE: This rebuilds the internal queue — use sparingly.
        Returns count of removed items.
        """
        removed = 0
        retained = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                if item.priority == int(priority):
                    removed += 1
                else:
                    retained.append(item)
            except asyncio.QueueEmpty:
                break
        for item in retained:
            self._queue.put_nowait(item)
        logger.debug(f"Cleared {removed} messages of priority {priority.name}")
        return removed
