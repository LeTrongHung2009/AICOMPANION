"""
companion/desktop/overlay_manager.py
====================================
Overlay and Work area geometry detector.
Reads active desktop sizes and screens to determine best display margins.
"""

from __future__ import annotations

import logging
import shutil
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect

from companion.utils.async_helpers import run_subprocess, sync_to_async

logger = logging.getLogger(__name__)

class DesktopGeometryTracker:
    """
    Identifies screen sizes and location of active windows using xdotool if available on Arch Linux.
    Avoids mapping companion widget on top of primary workspace.
    """

    def __init__(self) -> None:
        self._xdotool_available = shutil.which("xdotool") is not None
        if not self._xdotool_available:
            logger.warning("xdotool not found. Window avoidance will be disabled.")

    async def get_active_window_geometry(self) -> QRect | None:
        """
        Query X11 window geometry using xdotool subprocess safely.
        
        Returns:
            QRect mapping coordinates, or None.
        """
        if not self._xdotool_available:
            return None

        try:
            # 1. Get active window ID
            rc, stdout, stderr = await run_subprocess(["xdotool", "getactivewindow"])
            if rc != 0 or not stdout:
                return None
            window_id = stdout.strip()

            # 2. Get geometry of window
            rc, stdout, stderr = await run_subprocess(["xdotool", "getwindowgeometry", window_id])
            if rc != 0 or not stdout:
                return None

            # Parse dimensions from output
            # Output pattern:
            # Window 48234499
            #   Position: 200,100 (screen: 0)
            #   Geometry: 1200x800
            lines = stdout.split("\n")
            pos_line = next((l for l in lines if "Position:" in l), None)
            geom_line = next((l for l in lines if "Geometry:" in l), None)

            if pos_line and geom_line:
                # Extract x, y
                pos_str = pos_line.split("Position:")[1].split("(")[0].strip()
                x, y = map(int, pos_str.split(","))
                # Extract w, h
                geom_str = geom_line.split("Geometry:")[1].strip()
                w, h = map(int, geom_str.split("x"))
                return QRect(x, y, w, h)
        except Exception as exc:
            logger.debug(f"Failed to query active window geometry: {exc}")
        
        return None

    def get_desktop_work_area(self) -> QRect:
        """Get standard desktop screen size via PyQt6."""
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            geom = primary_screen.availableGeometry()
            return QRect(geom.x(), geom.y(), geom.width(), geom.height())
        return QRect(0, 0, 1920, 1080)
