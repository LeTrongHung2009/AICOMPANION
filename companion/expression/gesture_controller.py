"""
companion/expression/gesture_controller.py
==========================================
Gesture Controller.
Calculates dynamic values (like breathing, nodding, looking around, eye blinking)
to send as custom parameters to VTube Studio for active visual presence.
"""

from __future__ import annotations

import math
import time

class GestureController:
    """
    Generates dynamic parameter overrides to make the Live2D model look alive.
    Includes breathing cycle, random blinking, and micro eye/head looking drift.
    """

    def __init__(self) -> None:
        self.start_time = time.monotonic()
        self.blink_state = 1.0  # Open
        self.last_blink_time = time.monotonic()
        self.blink_cooldown = 4.0

    def calculate_gestures(self) -> dict[str, float]:
        """
        Calculate target gesture param overrides.
        
        Returns:
            Dict of Live2D parameter name -> target float value.
        """
        now = time.monotonic()
        elapsed = now - self.start_time

        # 1. Breathing (sinusoidal ParamBreath)
        # Standard breathing rate: ~12-18 breaths per minute (frequency: ~0.2-0.3 Hz)
        breath = (math.sin(elapsed * 2.0 * math.pi * 0.25) + 1.0) / 2.0  # 0.0 to 1.0

        # 2. Eye Blinking state machine
        if now - self.last_blink_time > self.blink_cooldown:
            # Blink cycle: close eye, then open it
            blink_progress = now - self.last_blink_time - self.blink_cooldown
            if blink_progress < 0.15:
                self.blink_state = 0.0  # Closed
            elif blink_progress < 0.3:
                self.blink_state = 1.0  # Open
                self.last_blink_time = now
                import random
                self.blink_cooldown = random.uniform(2.5, 6.0)

        # 3. Micro-look drift (looking around slightly)
        # Slow random-looking walks
        look_x = math.sin(elapsed * 0.1) * 15.0
        look_y = math.cos(elapsed * 0.15) * 10.0

        return {
            "ParamBreath": breath,
            "ParamEyeOpenL": self.blink_state,
            "ParamEyeOpenR": self.blink_state,
            "ParamAngleX": look_x,
            "ParamAngleY": look_y,
            "ParamBodyAngleX": look_x * 0.5
        }
