"""
companion/model_setup/attribution.py
====================================
Attribution and compliance registry for official Live2D model assets.
Required for Booth PM #4711410. Ensures licensing is strictly adhered to.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

ATTRIBUTION_TEXT = """
======================================================================
                  LIVE2D MODEL ATTRIBUTION & LICENSE
======================================================================
This application is configured to interface with the following Live2D asset:
- Source: Booth PM #4711410 (Half-Body Live2D Avatar Model)
- URL: https://booth.pm/en/items/4711410

----------------------------------------------------------------------
CREDITS REQUIRED:
- Artist/Illustration: @koahri1
- Live2D Rigging: @MedL2D
----------------------------------------------------------------------
LICENSE TERMS:
- Free for personal, non-commercial use.
- Redistribution, resale, or claiming ownership of this asset is
  STRICTLY PROHIBITED.
- You must hold a valid copy of the model files under Booth license.
======================================================================
"""

def show_attribution() -> None:
    """Print the official attribution credits to the console."""
    print(ATTRIBUTION_TEXT)
    logger.info("Live2D Model Attribution shown.")

def get_credits_dict() -> dict[str, str]:
    """Get credits dictionary."""
    return {
        "model_id": "booth_4711410",
        "artist": "@koahri1",
        "rigging": "@MedL2D",
        "source_url": "https://booth.pm/en/items/4711410",
        "license": "Personal Non-Commercial Use Only"
    }
