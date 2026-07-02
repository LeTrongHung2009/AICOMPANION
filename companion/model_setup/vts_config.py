"""
companion/model_setup/vts_config.py
===================================
VTube Studio Config Setup for Booth PM #4711410.
Defines parameters, custom parameters, handshakes, and hotkey mappings.
"""

from __future__ import annotations

# Hotkey index maps for Booth PM #4711410 Live2D rig expressions
# Make sure to set these up inside VTube Studio accordingly.
HOTKEY_MAPPINGS = {
    "exp_happy": "KeyH",       # Triggers Happy Expression
    "exp_sad": "KeyS",         # Triggers Sad Expression
    "exp_angry": "KeyA",       # Triggers Angry Expression
    "exp_blush": "KeyB",       # Triggers Blush (Shy/Embarrassed)
    "exp_shock": "KeyO",       # Triggers Shocked / Wide-eyes
    "exp_reset": "KeyR",       # Resets all expressions
}

# Custom tracking parameter mappings to inject direct parameters
PARAMETER_MAPPINGS = {
    # System Emotion Mapping -> Live2D Parameter Name
    "valence": "ParamValence",           # Custom parameter for positive/negative affect
    "arousal": "ParamAura",              # Custom parameter for energy/excitedness
    "focus": "ParamFocus",               # Custom parameter for task concentration
}

VTS_APP_INFO = {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "pluginName": "MyCompanion AI",
    "pluginDeveloper": "MyCompanion Contributors",
    "authenticationToken": ""  # Saved dynamically after user approves handshake in VTS UI
}
