"""
companion/expression/vts_expression_map.py
==========================================
Deterministic matrix mapping systems 3-tier emotional space
(Base Mood, Complex Trait, Social Affect) directly to VTS hotkeys & params.
Complying with Booth PM #4711410.
"""

from __future__ import annotations

import logging
from companion.model_setup.vts_config import HOTKEY_MAPPINGS, LIVE2D_MODEL

logger = logging.getLogger(__name__)

class VTSExpressionMapper:
    """
    Translates 3-tier system emotions into VTS expressions, hotkeys, and parameter outputs.
    """

    @staticmethod
    def map_mood_to_hotkey(mood_state: dict) -> tuple[str, bool]:
        """
        Determines if a hotkey expression switch is required.
        
        Returns:
            Tuple of (hotkey_name, is_reset_required).
        """
        base_mood = mood_state.get("base_mood", "calm")
        social_affect = mood_state.get("social_affect", "warm")

        # Map base mood to specific expression hotkeys
        if base_mood == "happy" or base_mood == "excited":
            return HOTKEY_MAPPINGS["exp_happy"], False
        elif base_mood == "melancholy":
            return HOTKEY_MAPPINGS["exp_sad"], False
        elif base_mood == "tired" and social_affect == "shy":
            return HOTKEY_MAPPINGS["exp_blush"], False
        elif base_mood == "curious":
            return HOTKEY_MAPPINGS["exp_shock"], False
        
        # Default or calm: reset expressions
        return HOTKEY_MAPPINGS["exp_reset"], True

    @staticmethod
    def map_mood_to_parameters(mood_state: dict) -> dict[str, float]:
        """
        Maps emotional metrics directly to Live2D tracking input parameters.
        
        Returns:
            Dict of parameter name -> float value (usually -1.0 to 1.0 or 0.0 to 1.0).
        """
        valence = mood_state.get("valence", 0.5)  # 0.0 to 1.0
        arousal = mood_state.get("arousal", 0.5)  # 0.0 to 1.0
        complex_strength = mood_state.get("complex_strength", 0.5)

        # Scale parameters to standard VTS range (-1.0 to 1.0)
        # Valence maps ParamValence: low (-1.0) = sad, high (1.0) = happy
        param_valence = (valence * 2.0) - 1.0
        # Arousal maps ParamAura: high energy (1.0), low energy (-1.0)
        param_arousal = (arousal * 2.0) - 1.0
        # Focus maps concentration
        param_focus = complex_strength if mood_state.get("complex_trait") == "focused" else 0.0

        return {
            "ParamValence": param_valence,
            "ParamAura": param_arousal,
            "ParamFocus": param_focus
        }
