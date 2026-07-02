"""
companion/persona/emotion_complex.py
======================================
Tier 2 Emotion Layer — Complex Trait State.
Layered over base mood, representing more nuanced cognitive-emotional traits
that emerge from context, history, and personality.
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ComplexTrait(Enum):
    """Complex emotional traits (Tier 2)."""
    PLAYFUL = "playful"
    FOCUSED = "focused"
    EMPATHETIC = "empathetic"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    CAUTIOUS = "cautious"
    CONFIDENT = "confident"
    REFLECTIVE = "reflective"


# Which traits are compatible with which base moods
TRAIT_MOOD_AFFINITY: dict[ComplexTrait, list[str]] = {
    ComplexTrait.PLAYFUL: ["happy", "excited", "curious"],
    ComplexTrait.FOCUSED: ["calm", "curious", "analytical"],
    ComplexTrait.EMPATHETIC: ["calm", "melancholy", "happy"],
    ComplexTrait.ANALYTICAL: ["curious", "calm", "focused"],
    ComplexTrait.CREATIVE: ["excited", "curious", "happy"],
    ComplexTrait.CAUTIOUS: ["tired", "melancholy", "calm"],
    ComplexTrait.CONFIDENT: ["happy", "excited", "calm"],
    ComplexTrait.REFLECTIVE: ["melancholy", "calm", "tired"],
}

# Context keywords that trigger trait activation
TRAIT_TRIGGERS: dict[ComplexTrait, list[str]] = {
    ComplexTrait.PLAYFUL: ["trò", "đùa", "vui", "game", "haha", "lol"],
    ComplexTrait.FOCUSED: ["giúp", "code", "lỗi", "debug", "work", "làm"],
    ComplexTrait.EMPATHETIC: ["buồn", "mệt", "khó khăn", "stress", "lo lắng"],
    ComplexTrait.ANALYTICAL: ["tại sao", "how", "explain", "phân tích", "so sánh"],
    ComplexTrait.CREATIVE: ["ý tưởng", "idea", "creative", "thiết kế", "viết"],
    ComplexTrait.CAUTIOUS: ["cẩn thận", "nguy hiểm", "rủi ro", "không chắc"],
    ComplexTrait.CONFIDENT: ["chắc chắn", "tôi biết", "dễ thôi", "được rồi"],
    ComplexTrait.REFLECTIVE: ["nhớ lại", "hôm nay", "cảm thấy", "nghĩ rằng"],
}


@dataclass
class ComplexTraitState:
    """Active complex trait with strength and expiry."""
    trait: ComplexTrait = ComplexTrait.EMPATHETIC
    strength: float = 0.5  # 0.0-1.0
    activated_at: float = field(default_factory=time.monotonic)
    expires_at: float = field(default_factory=lambda: time.monotonic() + 180.0)

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "complex_trait": self.trait.value,
            "strength": round(self.strength, 2),
        }


class ComplexEmotionEngine:
    """
    Manages Tier 2 complex trait layer.
    Traits are activated by text context analysis and decay over time.
    """

    def __init__(self) -> None:
        self._active_trait = ComplexTraitState()
        self._trait_history: list[ComplexTrait] = []

    @property
    def state(self) -> ComplexTraitState:
        if self._active_trait.is_expired():
            self._select_default_trait()
        return self._active_trait

    @property
    def current_trait(self) -> ComplexTrait:
        return self.state.trait

    def analyze_text(self, text: str, base_mood: str = "calm") -> Optional[ComplexTrait]:
        """
        Analyze text to detect contextually appropriate trait.

        Args:
            text: User message or context text.
            base_mood: Current base mood for affinity check.

        Returns:
            Newly activated trait, or None if unchanged.
        """
        text_lower = text.lower()
        scores: dict[ComplexTrait, float] = {}

        for trait, keywords in TRAIT_TRIGGERS.items():
            score = sum(1.0 for kw in keywords if kw in text_lower)
            # Boost score if compatible with current base mood
            affinity_moods = TRAIT_MOOD_AFFINITY.get(trait, [])
            if base_mood in affinity_moods:
                score += 0.5
            if score > 0:
                scores[trait] = score

        if not scores:
            return None

        best_trait = max(scores, key=scores.get)
        strength = min(1.0, scores[best_trait] / 3.0 + 0.4)

        if best_trait != self._active_trait.trait or self._active_trait.is_expired():
            self._activate_trait(best_trait, strength)
            return best_trait

        return None

    def _activate_trait(self, trait: ComplexTrait, strength: float = 0.7) -> None:
        """Activate a trait with given strength, expiring after duration."""
        duration = random.uniform(120.0, 300.0)  # 2-5 minutes
        self._active_trait = ComplexTraitState(
            trait=trait,
            strength=strength,
            expires_at=time.monotonic() + duration,
        )
        self._trait_history.append(trait)
        if len(self._trait_history) > 20:
            self._trait_history.pop(0)

    def _select_default_trait(self) -> None:
        """Select a default trait when current one expires."""
        # Slightly favor previously seen traits for consistency
        if self._trait_history:
            recent = random.choice(self._trait_history[-5:])
            self._activate_trait(recent, strength=0.4)
        else:
            self._activate_trait(ComplexTrait.EMPATHETIC, strength=0.5)
