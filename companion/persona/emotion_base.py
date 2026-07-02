"""
companion/persona/emotion_base.py
===================================
Tier 1 Emotion Layer — Base Mood State.
Represents the fundamental emotional groundstate of the companion.
Uses a discrete state machine with smooth transition weights.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BaseMood(Enum):
    """Primary emotional states (Tier 1)."""
    HAPPY = "happy"
    CALM = "calm"
    CURIOUS = "curious"
    EXCITED = "excited"
    TIRED = "tired"
    MELANCHOLY = "melancholy"


# Transition weights: how likely to move from mood A to mood B
# Higher values = more likely transition
MOOD_TRANSITIONS: dict[BaseMood, dict[BaseMood, float]] = {
    BaseMood.HAPPY: {BaseMood.EXCITED: 0.3, BaseMood.CALM: 0.3, BaseMood.CURIOUS: 0.2, BaseMood.HAPPY: 0.2},
    BaseMood.CALM: {BaseMood.HAPPY: 0.25, BaseMood.CURIOUS: 0.3, BaseMood.CALM: 0.3, BaseMood.TIRED: 0.15},
    BaseMood.CURIOUS: {BaseMood.HAPPY: 0.3, BaseMood.EXCITED: 0.3, BaseMood.CALM: 0.2, BaseMood.CURIOUS: 0.2},
    BaseMood.EXCITED: {BaseMood.HAPPY: 0.4, BaseMood.CALM: 0.2, BaseMood.CURIOUS: 0.3, BaseMood.EXCITED: 0.1},
    BaseMood.TIRED: {BaseMood.CALM: 0.4, BaseMood.MELANCHOLY: 0.2, BaseMood.TIRED: 0.3, BaseMood.HAPPY: 0.1},
    BaseMood.MELANCHOLY: {BaseMood.CALM: 0.4, BaseMood.TIRED: 0.2, BaseMood.CURIOUS: 0.2, BaseMood.MELANCHOLY: 0.2},
}

# How user interaction affects mood
INTERACTION_EFFECTS: dict[str, dict[BaseMood, float]] = {
    "positive": {BaseMood.HAPPY: 0.3, BaseMood.EXCITED: 0.2, BaseMood.CURIOUS: 0.1},
    "negative": {BaseMood.MELANCHOLY: 0.2, BaseMood.TIRED: 0.1},
    "technical": {BaseMood.CURIOUS: 0.3, BaseMood.CALM: 0.2},
    "playful": {BaseMood.HAPPY: 0.2, BaseMood.EXCITED: 0.3},
    "neutral": {},
}


@dataclass
class BaseMoodState:
    """
    Current base mood with intensity and duration tracking.
    """
    mood: BaseMood = BaseMood.HAPPY
    intensity: float = 0.7  # 0.0 = barely present, 1.0 = very strong
    started_at: float = field(default_factory=time.monotonic)
    transition_due: float = field(default_factory=lambda: time.monotonic() + 300.0)

    # Valence-arousal representation
    valence: float = 0.6   # Positive/negative (0=negative, 1=positive)
    arousal: float = 0.5   # Energy level (0=calm, 1=excited)

    def to_dict(self) -> dict:
        return {
            "base_mood": self.mood.value,
            "intensity": round(self.intensity, 2),
            "valence": round(self.valence, 2),
            "arousal": round(self.arousal, 2),
        }


class BaseMoodEngine:
    """
    Manages the base mood state with natural drift and interaction-based updates.
    """

    # Mood → (valence, arousal) mapping
    MOOD_VA = {
        BaseMood.HAPPY: (0.8, 0.6),
        BaseMood.CALM: (0.6, 0.2),
        BaseMood.CURIOUS: (0.7, 0.7),
        BaseMood.EXCITED: (0.9, 0.9),
        BaseMood.TIRED: (0.4, 0.1),
        BaseMood.MELANCHOLY: (0.2, 0.3),
    }

    def __init__(self, initial_mood: BaseMood = BaseMood.HAPPY) -> None:
        v, a = self.MOOD_VA[initial_mood]
        self._state = BaseMoodState(
            mood=initial_mood,
            valence=v,
            arousal=a,
        )
        self._drift_interval = 300.0  # Natural drift every 5 minutes

    @property
    def state(self) -> BaseMoodState:
        return self._state

    @property
    def current_mood(self) -> BaseMood:
        return self._state.mood

    def tick(self) -> Optional[BaseMood]:
        """
        Check if a natural mood transition should occur.
        Call this periodically.

        Returns:
            New BaseMood if transition occurred, else None.
        """
        now = time.monotonic()
        if now >= self._state.transition_due:
            return self._natural_drift()
        return None

    def _natural_drift(self) -> BaseMood:
        """Apply a natural mood drift based on transition weights."""
        transitions = MOOD_TRANSITIONS[self._state.mood]
        moods = list(transitions.keys())
        weights = [transitions[m] for m in moods]

        new_mood = random.choices(moods, weights=weights, k=1)[0]
        self._apply_mood(new_mood, intensity_delta=-0.05)  # Slight fade
        # Next drift in 4-8 minutes
        self._state.transition_due = time.monotonic() + random.uniform(240, 480)
        return new_mood

    def apply_interaction(self, interaction_type: str = "neutral") -> None:
        """
        Modify mood based on interaction type.

        Args:
            interaction_type: One of positive, negative, technical, playful, neutral.
        """
        effects = INTERACTION_EFFECTS.get(interaction_type, {})
        if not effects:
            return

        # Find the most-affected mood
        target_mood = max(effects, key=effects.get)
        delta = max(effects.values())
        self._apply_mood(target_mood, intensity_delta=delta * 0.3)

    def _apply_mood(self, mood: BaseMood, intensity_delta: float = 0.0) -> None:
        """Transition to a new mood with smooth intensity adjustment."""
        if mood != self._state.mood:
            self._state.mood = mood
            self._state.started_at = time.monotonic()
            v, a = self.MOOD_VA[mood]
            self._state.valence = v
            self._state.arousal = a
            self._state.intensity = max(0.3, min(1.0, 0.6 + intensity_delta))
        else:
            self._state.intensity = max(0.3, min(1.0, self._state.intensity + intensity_delta))

    def force_mood(self, mood: BaseMood, intensity: float = 0.8) -> None:
        """Directly set a mood (e.g., from VTS event or user command)."""
        self._apply_mood(mood, intensity - 0.6)
        self._state.intensity = intensity
