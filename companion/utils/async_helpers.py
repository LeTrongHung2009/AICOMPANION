"""
companion/utils/async_helpers.py
=================================
Async utility functions for MyCompanion.
Helpers for timeouts, retries, throttling, and subprocess calls
that are Linux/Arch compatible.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Coroutine, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    default: Optional[T] = None,
    label: str = "task",
) -> Optional[T]:
    """
    Run a coroutine with a timeout, returning default on TimeoutError.

    Args:
        coro: The coroutine to run.
        timeout: Seconds before cancellation.
        default: Value to return on timeout.
        label: Label for logging.

    Returns:
        Result of coro or default on timeout.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"[{label}] Timed out after {timeout}s — returning default")
        return default
    except Exception as exc:
        logger.error(f"[{label}] Unexpected error: {exc}", exc_info=True)
        return default


async def retry_async(
    coro_fn: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    label: str = "async_op",
    **kwargs: Any,
) -> Optional[T]:
    """
    Retry an async function with exponential backoff.

    Args:
        coro_fn: Async function to retry.
        retries: Maximum retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay between retries.
        backoff_factor: Multiplier for each retry delay.
        exceptions: Exception types that trigger a retry.
        label: Label for logging.
    """
    delay = base_delay
    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except exceptions as exc:
            last_exc = exc
            if attempt == retries:
                logger.error(f"[{label}] All {retries} retries exhausted. Last error: {exc}")
                return None
            logger.warning(f"[{label}] Attempt {attempt + 1}/{retries} failed: {exc}. Retrying in {delay:.1f}s…")
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)

    return None


class AsyncThrottle:
    """
    Async rate throttle using a sliding window.
    Ensures at most `max_calls` per `period` seconds.
    """

    def __init__(self, max_calls: int, period: float) -> None:
        self.max_calls = max_calls
        self.period = period
        self._calls: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Block until a call slot is available."""
        async with self._lock:
            now = time.monotonic()
            # Purge expired entries
            self._calls = [t for t in self._calls if now - t < self.period]
            if len(self._calls) >= self.max_calls:
                wait_time = self.period - (now - self._calls[0])
                logger.debug(f"Throttle: waiting {wait_time:.2f}s for slot")
                await asyncio.sleep(max(0, wait_time))
                # Re-purge after wait
                now = time.monotonic()
                self._calls = [t for t in self._calls if now - t < self.period]
            self._calls.append(time.monotonic())

    async def __aenter__(self) -> "AsyncThrottle":
        await self.acquire()
        return self

    async def __aexit__(self, *_: Any) -> None:
        pass


async def run_subprocess(
    cmd: list[str],
    timeout: float = 30.0,
    check: bool = False,
) -> tuple[int, str, str]:
    """
    Run a subprocess asynchronously. Linux/Arch compatible.

    Args:
        cmd: Command and arguments list.
        timeout: Seconds before kill.
        check: Raise on non-zero exit if True.

    Returns:
        Tuple of (return_code, stdout, stderr).

    Raises:
        RuntimeError: If check=True and return code is non-zero.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        rc = proc.returncode or 0
        if check and rc != 0:
            raise RuntimeError(f"Command {cmd!r} failed (rc={rc}): {stderr}")
        return rc, stdout, stderr
    except asyncio.TimeoutError:
        logger.error(f"Subprocess timed out: {cmd}")
        raise RuntimeError(f"Subprocess timed out: {cmd}")
    except FileNotFoundError as exc:
        logger.error(f"Executable not found: {cmd[0]}")
        raise RuntimeError(f"Executable not found: {cmd[0]}") from exc


def sync_to_async(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Wrap a blocking synchronous function to run in a thread pool.
    Prevents blocking the asyncio event loop.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
    return wrapper


async def sleep_interruptible(
    duration: float,
    check_fn: Optional[Callable[[], bool]] = None,
    poll_interval: float = 0.5,
) -> bool:
    """
    Sleep for duration seconds, but can be interrupted if check_fn returns True.

    Args:
        duration: Total sleep time.
        check_fn: Optional callable returning True to interrupt early.
        poll_interval: How often to check check_fn.

    Returns:
        True if completed normally, False if interrupted.
    """
    elapsed = 0.0
    while elapsed < duration:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        if check_fn is not None and check_fn():
            return False
    return True
