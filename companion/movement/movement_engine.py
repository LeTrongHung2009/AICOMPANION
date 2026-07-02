"""
companion/movement/movement_engine.py
=====================================
Desktop Movement Engine.
Animates micro-movements when the user is idle (>120s) and shifts position
to avoid overlaying active IDE workspace coordinates.
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPoint, QRect

from companion.movement.workspace_detector import WorkspaceDetector
from companion.movement.drift_calculator import DriftCalculator

logger = logging.getLogger(__name__)

class MovementEngine:
    """
    Subtle motion planner for the companion window.
    Shifts the widget gently and pushes it out of active IDE rect overlaps.
    """

    def __init__(self, widget: QWidget, idle_threshold: float = 120.0) -> None:
        self.widget = widget
        self.idle_threshold = idle_threshold
        self.detector = WorkspaceDetector()
        self.drift_calc = DriftCalculator()

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_interaction_time = time.monotonic()
        self._base_position = widget.pos()

    def update_interaction_time(self) -> None:
        """Called to reset the idle timer and log baseline coordinate positions."""
        self._last_interaction_time = time.monotonic()
        self._base_position = self.widget.pos()

    async def start(self) -> None:
        """Start the movement animation thread loop."""
        if self._running:
            return
        self._running = True
        self.update_interaction_time()
        self._task = asyncio.create_task(self._animation_loop(), name="movement_engine")
        logger.info(f"Movement engine active (idle_threshold={self.idle_threshold}s)")

    async def stop(self) -> None:
        """Stop the movement engine."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Movement engine stopped")

    async def _animation_loop(self) -> None:
        elapsed = 0.0
        while self._running:
            try:
                await asyncio.sleep(0.1)  # 10 Hz refresh
                idle_duration = time.monotonic() - self._last_interaction_time

                if idle_duration > self.idle_threshold:
                    elapsed += 0.1
                    await self._perform_drift(elapsed)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in Movement loop: {exc}")

    async def _perform_drift(self, elapsed: float) -> None:
        # Calculate lissajous drift
        offset = self.drift_calc.calculate_lissajous(elapsed)
        target_pos = self._base_position + offset

        # Query work area bounds
        screen = self.detector.get_screen_bounds()
        widget_rect = QRect(target_pos, self.widget.size())

        # Check foreground active window intersection
        avoidance_rect = await self.detector.get_avoidance_rect()
        if avoidance_rect and widget_rect.intersects(avoidance_rect):
            # Resolve conflict: push widget towards closest screen corner
            target_pos = self._resolve_intersection(widget_rect, avoidance_rect, screen)
            # Rebase baseline coordinate to prevent snap back
            self._base_position = target_pos

        # Clamp boundaries inside screen
        x = max(screen.left(), min(screen.right() - self.widget.width(), target_pos.x()))
        y = max(screen.top(), min(screen.bottom() - self.widget.height(), target_pos.y()))
        
        # Smooth Qt move
        self.widget.move(x, y)

    def _resolve_intersection(self, widget_rect: QRect, avoidance_rect: QRect, screen: QRect) -> QPoint:
        # Push coordinate output away from collision rect margins
        # Check coordinates and push towards right or bottom edge
        target_x = widget_rect.x()
        target_y = widget_rect.y()

        if avoidance_rect.right() > widget_rect.left() and avoidance_rect.left() < widget_rect.right():
            # If overlap, shift to right side or left side
            dist_right = abs(avoidance_rect.right() - widget_rect.left())
            dist_left = abs(widget_rect.right() - avoidance_rect.left())
            if dist_right < dist_left:
                target_x = avoidance_rect.right() + 10
            else:
                target_x = avoidance_rect.left() - widget_rect.width() - 10

        return QPoint(target_x, target_y)
