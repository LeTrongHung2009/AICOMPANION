"""
companion/senses/screen_capture.py
=====================================
Screen capture module using mss for X11/Wayland on Arch Linux.
Captures the primary monitor and returns raw pixel data.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import mss
    import mss.tools
    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False
    logger.warning("mss not installed — screen capture disabled")


class ScreenCapture:
    """
    Captures screenshots using mss library.
    Arch Linux compatible (X11 and Wayland with XWayland).
    """

    def __init__(self, monitor_index: int = 1) -> None:
        """
        Args:
            monitor_index: Monitor to capture. 1 = primary, 0 = all monitors combined.
        """
        self.monitor_index = monitor_index
        self._available = _MSS_AVAILABLE

    def capture_raw(self) -> Optional[bytes]:
        """
        Capture the screen and return raw PNG bytes.

        Returns:
            PNG image bytes, or None if capture fails.
        """
        if not self._available:
            return None

        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                if self.monitor_index >= len(monitors):
                    idx = 1  # Fall back to primary
                else:
                    idx = self.monitor_index
                monitor = monitors[idx]
                screenshot = sct.grab(monitor)
                # Convert to PNG bytes
                png_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
                return png_bytes
        except Exception as exc:
            logger.error(f"Screen capture failed: {exc}", exc_info=True)
            return None

    def get_monitor_info(self) -> dict:
        """Return information about available monitors."""
        if not self._available:
            return {"available": False}
        try:
            with mss.mss() as sct:
                return {
                    "available": True,
                    "monitor_count": len(sct.monitors) - 1,  # Exclude virtual all-monitor
                    "monitors": [
                        {"index": i, "width": m["width"], "height": m["height"]}
                        for i, m in enumerate(sct.monitors)
                        if i > 0
                    ],
                }
        except Exception as exc:
            return {"available": False, "error": str(exc)}
