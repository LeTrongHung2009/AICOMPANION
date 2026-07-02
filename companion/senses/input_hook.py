"""
companion/senses/input_hook.py
===============================
Global Input Hook for Desktop Autonomy.
Monitors keyboard/mouse state and active window.
Used by Action Planner to understand user activity.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable
from pynput import mouse, keyboard

logger = logging.getLogger(__name__)

class InputHook:
    """
    Global input monitor using pynput.
    Tracks:
    - Last input timestamp
    - Active window title (via xdotool)
    - Mouse position
    - Keyboard activity
    """
    
    def __init__(self) -> None:
        self.last_input_time: float = 0.0
        self.active_window: Optional[str] = None
        self.mouse_position: tuple[int, int] = (0, 0)
        self.is_typing: bool = False
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._running: bool = False
        self._callbacks: list[Callable] = []
    
    async def start(self) -> None:
        """Start monitoring input events."""
        if self._running:
            return
        
        self._running = True
        logger.info("InputHook started - monitoring keyboard/mouse")
        
        # Start listeners in background threads
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self._mouse_listener.start()
        
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._keyboard_listener.start()
        
        # Start active window polling
        asyncio.create_task(self._poll_active_window())
    
    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener.join()
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener.join()
        
        logger.info("InputHook stopped")
    
    def _on_mouse_move(self, x: int, y: int) -> None:
        """Handle mouse movement."""
        import time
        self.last_input_time = time.time()
        self.mouse_position = (x, y)
    
    def _on_mouse_click(self, x: int, y: int, button, pressed: bool) -> None:
        """Handle mouse click."""
        import time
        if pressed:
            self.last_input_time = time.time()
            self._notify_callbacks("mouse_click", {"x": x, "y": y, "button": str(button)})
    
    def _on_mouse_scroll(self, x: int, y: int, dx, dy) -> None:
        """Handle mouse scroll."""
        import time
        self.last_input_time = time.time()
    
    def _on_key_press(self, key) -> None:
        """Handle key press."""
        import time
        self.last_input_time = time.time()
        self.is_typing = True
        try:
            key_char = key.char if hasattr(key, 'char') else str(key)
            self._notify_callbacks("key_press", {"key": key_char})
        except Exception as e:
            logger.debug(f"Key press event: {key}")
    
    def _on_key_release(self, key) -> None:
        """Handle key release."""
        self.is_typing = False
    
    async def _poll_active_window(self) -> None:
        """Poll active window title every 2 seconds."""
        import subprocess
        
        while self._running:
            try:
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "getactivewindow", "getwindowname",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL
                )
                stdout, _ = await result.communicate()
                if stdout:
                    self.active_window = stdout.decode().strip()
            except Exception as e:
                logger.debug(f"Failed to get active window: {e}")
            
            await asyncio.sleep(2.0)
    
    def add_callback(self, callback: Callable) -> None:
        """Add callback for input events."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, event_type: str, data: dict) -> None:
        """Notify all callbacks of an event."""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_idle_time(self) -> float:
        """Get seconds since last input."""
        import time
        if self.last_input_time == 0:
            return float('inf')
        return time.time() - self.last_input_time
    
    def is_user_active(self, threshold: float = 30.0) -> bool:
        """Check if user is currently active."""
        return self.get_idle_time() < threshold
    
    def get_context(self) -> dict:
        """Get current input context."""
        return {
            "active_window": self.active_window,
            "mouse_position": self.mouse_position,
            "is_typing": self.is_typing,
            "idle_time": self.get_idle_time(),
        }


# Singleton instance
_hook_instance: Optional[InputHook] = None

def get_input_hook() -> Optional[InputHook]:
    """Get the global InputHook instance."""
    global _hook_instance
    return _hook_instance

def create_input_hook() -> InputHook:
    """Create the global InputHook instance."""
    global _hook_instance
    if _hook_instance is None:
        _hook_instance = InputHook()
    return _hook_instance
