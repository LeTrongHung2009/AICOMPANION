"""
companion/movement/workspace_detector.py
========================================
Active Window and Workspace Monitor.
Wraps geometry tracker queries to check if widget boundaries intersect
with the user's primary code editor or web browser window.
"""

from __future__ import annotations

import logging
from PyQt6.QtCore import QRect
from companion.desktop.overlay_manager import DesktopGeometryTracker

logger = logging.getLogger(__name__)

class WorkspaceDetector:
    """
    Evaluates where active workspace applications are placed to steer
    companion drift coordinates away from intersection hotspots.
    """

    def __init__(self) -> None:
        self._tracker = DesktopGeometryTracker()

    async def get_avoidance_rect(self) -> QRect | None:
        """
        Query geometry of the main foreground window.
        
        Returns:
            QRect representation or None.
        """
        return await self._tracker.get_active_window_geometry()

    def get_screen_bounds(self) -> QRect:
        """Returns bounds of the primary screen desktop area."""
        return self._tracker.get_desktop_work_area()
