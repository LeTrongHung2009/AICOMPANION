"""
companion/movement/drift_calculator.py
======================================
Mathematical drift trajectory calculators.
Generates smooth Lissajous curves or low-frequency jitter steps.
"""

from __future__ import annotations

import math
import random
from PyQt6.QtCore import QPoint

class DriftCalculator:
    """
    Calculates dynamic coordinate offsets relative to a base point.
    Prevents static desktop layout while avoiding sudden jerky steps.
    """

    def __init__(self, amplitude_x: float = 30.0, amplitude_y: float = 20.0) -> None:
        self.amp_x = amplitude_x
        self.amp_y = amplitude_y
        self.time_offset = random.uniform(0, 100)

    def calculate_lissajous(self, elapsed_seconds: float) -> QPoint:
        """
        Compute continuous parametric coordinate offset.
        
        Args:
            elapsed_seconds: Relative execution time.
            
        Returns:
            QPoint offset vector.
        """
        # Lissajous curve parameters
        # x = A * sin(a * t + delta)
        # y = B * sin(b * t)
        t = elapsed_seconds + self.time_offset
        dx = self.amp_x * math.sin(0.4 * t)
        dy = self.amp_y * math.cos(0.3 * t)
        return QPoint(int(dx), int(dy))

    def calculate_micro_jitter(self) -> QPoint:
        """Generate subtle random jitter offset."""
        dx = random.uniform(-2, 2)
        dy = random.uniform(-1, 1)
        return QPoint(int(dx), int(dy))
