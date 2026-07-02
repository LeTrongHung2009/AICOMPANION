"""
companion/persona/dialogue_style.py
===================================
Dialogue Style Engine.
Post-processes the AI's generated response to match current emotional state.
Adds speech patterns, punctuation styles, or quirks depending on mood.
"""

from __future__ import annotations

import re
import random

class DialogueStyle:
    """
    Polishes the raw response string to align with emotional metrics.
    For example:
    - Excited: Adds exclamation marks, caps some words, energetic suffixes.
    - Tired: Lacks punctuation capitalization, adds sighing markers.
    - Shy/Reserved: Adds hesitation indicators (..., ah, um).
    """

    @staticmethod
    def style_response(text: str, mood_state: dict) -> str:
        if not text:
            return text

        base_mood = mood_state.get("base_mood", "calm")
        complex_trait = mood_state.get("complex_trait", "empathetic")
        social_affect = mood_state.get("social_affect", "warm")

        # Normalize text to remove markdown format since widget needs plain text
        cleaned = re.sub(r'[*_`~#\[\]]', '', text)

        # Apply stylistic overlays based on base mood
        if base_mood == "excited":
            # Add energy
            cleaned = cleaned.replace(".", "!")
            if not cleaned.endswith("!"):
                cleaned += "!"
            if random.random() < 0.3:
                cleaned += " Hí hí~"
        elif base_mood == "tired":
            # Lowercase start, slow pace
            cleaned = cleaned[0].lower() + cleaned[1:] if cleaned else cleaned
            cleaned = cleaned.replace("!", ".")
            if random.random() < 0.4:
                cleaned = "Oáp... " + cleaned
        elif base_mood == "melancholy":
            cleaned = cleaned.replace("!", ".")
            if not cleaned.endswith("..."):
                cleaned = cleaned.rstrip(".") + "..."

        # Apply overlays based on social affect
        if social_affect == "teasing":
            if random.random() < 0.5:
                cleaned += " :p"
        elif social_affect == "shy":
            if random.random() < 0.6:
                cleaned = "À... " + cleaned.replace(", ", "... ")

        return cleaned
