"""
companion/dream/log_compressor.py
==================================
Log Compressor.
Aggregates daily conversational chat entries into clean transcripts
suitable for LLM memory synthesis prompts.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LogCompressor:
    """
    Condenses conversation rows into a compact structured string.
    Removes system markers and metadata clutter.
    """

    @staticmethod
    def compress_logs(conversation_rows: list[dict]) -> str:
        """
        Compile log objects into readable summaries.
        
        Args:
            conversation_rows: List of {"role": "...", "content": "..."}
            
        Returns:
            Formatted script transcript.
        """
        if not conversation_rows:
            return "No interactions logged today."

        lines = []
        for row in conversation_rows:
            role = row.get("role", "unknown").upper()
            content = row.get("content", "").strip()
            # Parse timestamp if available
            ts_val = row.get("timestamp")
            time_str = ""
            if ts_val:
                try:
                    time_str = f"[{datetime.fromtimestamp(ts_val).strftime('%H:%M')}] "
                except Exception:
                    pass
            lines.append(f"{time_str}{role}: {content}")

        return "\n".join(lines)
