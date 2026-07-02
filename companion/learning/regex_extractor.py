"""
companion/learning/regex_extractor.py
=====================================
Regex Fact Extractor.
Extracts simple facts locally using fast regex searches
to avoid executing LLM tasks for obvious items.
"""

from __future__ import annotations

import re

# Match patterns: (regex pattern, fact_type, text template)
PATTERNS = [
    # Identity: name
    (r"(?:tên tôi là|tên tớ là|tên mình là|tôi tên là|gọi tôi là|gọi mình là)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,15})", "identity", "Tên chủ nhân: {}"),
    # Preferences
    (r"(?:mình thích|tớ thích|tôi thích|mình rất thích)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,20})", "preference", "Chủ nhân thích {}"),
    # Aversions
    (r"(?:mình ghét|tớ ghét|tôi ghét|mình không thích)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,20})", "aversion", "Chủ nhân không thích {}"),
    # Goals
    (r"(?:muốn học|đang học|muốn làm)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,30})", "goal", "Chủ nhân muốn học/làm {}")
]

class RegexExtractor:
    """
    Scans incoming text string for immediate regex facts.
    """

    @staticmethod
    def extract_facts(text: str) -> list[dict]:
        """
        Scan and return matches.
        """
        extracted = []
        for regex, fact_type, template in PATTERNS:
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Exclude strings that are too long
                if len(value) < 40:
                    fact_content = template.format(value)
                    extracted.append({
                        "type": fact_type,
                        "fact": fact_content,
                        "confidence": 0.95  # Regex fits are high confidence
                    })
        return extracted
