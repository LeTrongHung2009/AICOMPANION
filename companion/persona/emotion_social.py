"""
companion/persona/emotion_social.py
====================================
Tier 3 Emotion Layer — Social Affect State.
Defines the social presentation, warmth, politeness, and alignment with the user.
Fades or intensifies based on social cues, feedback, and session history.
"""

from __future__ import annotations

import time
from enum import Enum
from dataclasses import dataclass, field

class SocialAffect(Enum):
    """Social affects (Tier 3)."""
    WARM = "warm"
    PROFESSIONAL = "professional"
    BORED = "bored"
    SHY = "shy"
    RESERVED = "reserved"
    TEASING = "teasing"

@dataclass
class SocialAffectState:
    """Active social affect representing relationship/interaction dynamic."""
    affect: SocialAffect = SocialAffect.WARM
    intensity: float = 0.5  # 0.0-1.0
    alignment_score: float = 0.5  # User affinity rating (0.0 = cold, 1.0 = deep trust)
    updated_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict:
        return {
            "social_affect": self.affect.value,
            "intensity": round(self.intensity, 2),
            "alignment": round(self.alignment_score, 2)
        }

class SocialAffectEngine:
    """
    Manages Tier 3 social affect layer.
    Determines politeness/distance/warmth based on alignment score and conversation sentiment.
    """

    def __init__(self) -> None:
        self._state = SocialAffectState()

    @property
    def state(self) -> SocialAffectState:
        return self._state

    @property
    def current_affect(self) -> SocialAffect:
        return self._state.affect

    def process_feedback(self, sentiment: str) -> None:
        """
        Adjust social affect and alignment score based on dialogue feedback/sentiment.
        
        Args:
            sentiment: positive, negative, neutral
        """
        now = time.monotonic()
        self._state.updated_at = now
        
        if sentiment == "positive":
            self._state.alignment_score = min(1.0, self._state.alignment_score + 0.05)
            self._state.intensity = min(1.0, self._state.intensity + 0.02)
            if self._state.alignment_score > 0.8:
                self._state.affect = SocialAffect.WARM
            elif self._state.alignment_score > 0.6:
                self._state.affect = SocialAffect.TEASING
        elif sentiment == "negative":
            self._state.alignment_score = max(0.0, self._state.alignment_score - 0.08)
            self._state.intensity = min(1.0, self._state.intensity + 0.05)  # stress/defensiveness raises intensity
            if self._state.alignment_score < 0.3:
                self._state.affect = SocialAffect.RESERVED
            else:
                self._state.affect = SocialAffect.PROFESSIONAL
        else:  # neutral
            # Natural decay towards base alignment
            self._state.intensity = max(0.1, self._state.intensity - 0.01)
            # Slow change back to basic warm/professional affect
            if self._state.alignment_score >= 0.5:
                self._state.affect = SocialAffect.WARM
            else:
                self._state.affect = SocialAffect.PROFESSIONAL

    def set_alignment(self, score: float) -> None:
        """Explicitly set the alignment rating."""
        self._state.alignment_score = max(0.0, min(1.0, score))
        self._state.updated_at = time.monotonic()
