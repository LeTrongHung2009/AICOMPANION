"""
companion/persona/mood_engine.py
================================
Consolidated Emotion Engine.
Wires together BaseMoodEngine (Tier 1), ComplexEmotionEngine (Tier 2), and SocialAffectEngine (Tier 3).
Provides a unified state accessor and handles mood updates.
"""

from __future__ import annotations

import logging
from typing import Optional

from companion.persona.emotion_base import BaseMoodEngine, BaseMood
from companion.persona.emotion_complex import ComplexEmotionEngine, ComplexTrait
from companion.persona.emotion_social import SocialAffectEngine, SocialAffect
from companion.utils.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger(__name__)

class MoodEngine:
    """
    Orchestrator for the 3-tier emotional space of MyCompanion.
    Publishes MOOD_CHANGED events to the EventBus.
    """

    def __init__(self) -> None:
        self.base_engine = BaseMoodEngine(BaseMood.HAPPY)
        self.complex_engine = ComplexEmotionEngine()
        self.social_engine = SocialAffectEngine()
        self._bus = get_event_bus()

    def get_mood_state(self) -> dict:
        """
        Get the current combined emotional state.
        
        Returns:
            Dict containing base_mood, complex_trait, and social_affect details.
        """
        base = self.base_engine.state.to_dict()
        complex_state = self.complex_engine.state.to_dict()
        social = self.social_engine.state.to_dict()
        
        return {
            "base_mood": base["base_mood"],
            "base_intensity": base["intensity"],
            "valence": base["valence"],
            "arousal": base["arousal"],
            "complex_trait": complex_state["complex_trait"],
            "complex_strength": complex_state["strength"],
            "social_affect": social["social_affect"],
            "social_intensity": social["intensity"],
            "alignment": social["alignment"]
        }

    def update_from_interaction(self, user_text: str, response_sentiment: str) -> None:
        """
        Process a user transaction to update all emotional layers.
        
        Args:
            user_text: The user's input text (to extract complex traits).
            response_sentiment: Sentiment of the interaction (positive, negative, technical, neutral).
        """
        old_state = self.get_mood_state()
        
        # 1. Base Mood interaction
        self.base_engine.apply_interaction(response_sentiment)
        
        # 2. Complex Trait extraction
        self.complex_engine.analyze_text(user_text, self.base_engine.current_mood.value)
        
        # 3. Social Affect update
        self.social_engine.process_feedback(response_sentiment)
        
        new_state = self.get_mood_state()
        if new_state["base_mood"] != old_state["base_mood"] or new_state["complex_trait"] != old_state["complex_trait"] or new_state["social_affect"] != old_state["social_affect"]:
            logger.info(f"Mood state changed: {old_state['base_mood']} -> {new_state['base_mood']}")
            self._bus.emit_sync(Event(
                type=EventType.MOOD_CHANGED,
                data=new_state,
                source="mood_engine"
            ))

    def tick(self) -> None:
        """Periodic update called by orchestrator. Allows natural emotional drift."""
        old_mood = self.base_engine.current_mood
        drifted = self.base_engine.tick()
        if drifted:
            new_state = self.get_mood_state()
            self._bus.emit_sync(Event(
                type=EventType.MOOD_CHANGED,
                data=new_state,
                source="mood_engine"
            ))
