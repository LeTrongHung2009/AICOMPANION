#!/usr/bin/env python3
"""
generate_project.py
===================
Meta-generator script to recreate the entire modular structure of MyCompanion framework.
Useful for packaging and deployment.
"""

import os
from pathlib import Path

# Segments data
FILES_DATA = {
    "requirements.txt": """PyQt6>=6.4.0
sounddevice>=0.4.6
numpy>=1.23.0
mss>=9.0.0
websockets>=11.0.0
psutil>=5.9.0
edge-tts>=6.1.0
python-dotenv>=1.0.0
httpx>=0.24.0
Pillow>=9.5.0
tiktoken>=0.4.0""",

    ".env.example": """GROQ_API_KEY=gsk_your_groq_key_here
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
ENABLE_VISION=true
ENABLE_STT=true
ENABLE_TTS=true
ENABLE_VTS=true
ENABLE_MOVEMENT=true
MOVEMENT_IDLE_THRESHOLD=120.0
BOREDOM_IDLE_THRESHOLD=300.0
DREAM_IDLE_THRESHOLD=600.0
DREAM_CYCLE_DURATION=600.0
VISION_CAPTURE_INTERVAL=30.0
VISION_JPEG_QUALITY=60
STT_SAMPLE_RATE=16000
TTS_VOICE=vi-VN-HoaiMyNeural
TTS_PLAYER=mpv""",

    "companion/model_setup/attribution.py": '''"""
companion/model_setup/attribution.py
====================================
Attribution and compliance registry for official Live2D model assets.
Required for Booth PM #4711410.
"""
ATTRIBUTION_TEXT = """
======================================================================
                  LIVE2D MODEL ATTRIBUTION & LICENSE
======================================================================
Booth PM #4711410
Artist: @koahri1
Live2D Rigging: @MedL2D
======================================================================
"""
def show_attribution():
    print(ATTRIBUTION_TEXT)
'''
}

def generate():
    print("Starting meta generation...")
    for rel_path, content in FILES_DATA.items():
        p = Path(rel_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content.strip(), encoding="utf-8")
        print(f"Generated: {rel_path}")
    print("Done!")

if __name__ == "__main__":
    generate()
