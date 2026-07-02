"""
companion/desktop/input_field.py
================================
Text entry component.
Subclasses QLineEdit, adds custom theme and hotkeys.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import pyqtSignal, Qt

from companion.desktop.theme import INPUT_STYLE

class ChatInputField(QLineEdit):
    """
    Styled line edit field for sending text inputs.
    Emits submit signal when Return/Enter is pressed.
    """
    submitted = pyqtSignal(str)
    escaped = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Gõ tin nhắn...")
        self.setStyleSheet(INPUT_STYLE)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            text = self.text().strip()
            if text:
                self.submitted.emit(text)
                self.clear()
        elif event.key() == Qt.Key.Key_Escape:
            self.escaped.emit()
        else:
            super().keyPressEvent(event)
