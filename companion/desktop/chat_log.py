"""
companion/desktop/chat_log.py
=============================
Chat Log viewer widget.
Uses QTextBrowser supporting HTML formats, scrolling automatically.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtCore import Qt

from companion.desktop.theme import CHAT_MESSAGE_TEMPLATE, SCROLLBAR_STYLE

class ChatLog(QTextBrowser):
    """
    Read-only chat message feed window with custom styles.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setOpenExternalLinks(True)
        
        # Apply style properties
        self.setStyleSheet(f"QTextBrowser {{ background: transparent; border: none; }} {SCROLLBAR_STYLE}")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def append_message(self, sender: str, text: str, is_user: bool = False) -> None:
        """Add a new message bubble representation."""
        color = "#a78bfa" if not is_user else "#34d399"  # Violet vs Green
        html_msg = CHAT_MESSAGE_TEMPLATE.format(
            color=color,
            sender=sender,
            text=text
        )
        self.append(html_msg)
        # Smooth scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
