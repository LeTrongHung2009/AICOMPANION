"""
companion/learning/fact_classifier.py
=====================================
Fact Classifier.
Categorizes fact types (preference, aversion, identity, goal)
based on keywords or patterns before storing them.
"""

from __future__ import annotations

import re

class FactClassifier:
    """
    Identifies fact categories and confidence adjustments.
    """

    CATEGORIES = {
        "preference": [r"\b(thích|yêu|chuộng|mê|khoái)\b"],
        "aversion": [r"\b(ghét|sợ|không thích|dị ứng|anti)\b"],
        "identity": [r"\b(tên là|tớ là|mình là|làm nghề|lập trình viên|designer)\b"],
        "goal": [r"\b(muốn|định|cố gắng|mục tiêu|học cách|dự án)\b"]
    }

    @classmethod
    def classify(cls, fact_text: str) -> str:
        """
        Classifies fact text category.
        
        Returns:
            Type string.
        """
        text = fact_text.lower()
        for cat, patterns in cls.CATEGORIES.items():
            for pat in patterns:
                if re.search(pat, text):
                    return cat
        return "memory"  # default general category
