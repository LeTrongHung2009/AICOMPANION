"""
companion/desktop/chat_widget.py
================================
Main Chat Widget UI window using PyQt6.
Frameless, transparent backdrop, always-on-top, draggable, collapsible input field.
"""

from __future__ import annotations

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QPoint, pyqtSignal

from companion.desktop.chat_log import ChatLog
from companion.desktop.input_field import ChatInputField
from companion.desktop.theme import WIDGET_STYLE
from companion.utils.event_bus import get_event_bus, EventType, Event

logger = logging.getLogger(__name__)

class ChatWidget(QWidget):
    """
    Main Overlay Chat Interface.
    Draggable by holding left-click anywhere on the blank backdrop area.
    """
    text_submitted = pyqtSignal(str)

    def __init__(self, width: int = 320, height: int = 400, companion_name: str = "Hana") -> None:
        super().__init__()
        self._companion_name = companion_name
        self._drag_position = QPoint()
        self._bus = get_event_bus()

        self.setWindowTitle("MyCompanion")
        self.resize(width, height)

        # 1. Window Flag configuration (frameless, transparent, always-on-top)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Hides application icon from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("MainWidget")
        self.setStyleSheet(WIDGET_STYLE)

        # 2. Main layout setup
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(6)

        # Add header/drag area
        self._header = QWidget()
        self._header_layout = QHBoxLayout(self._header)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header.setFixedHeight(20)
        
        self._close_btn = QPushButton("×")
        self._close_btn.setFixedSize(16, 16)
        self._close_btn.setStyleSheet(
            "QPushButton { background: rgba(239, 68, 68, 0.4); color: white; border: none; border-radius: 8px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.9); }"
        )
        self._close_btn.clicked.connect(self.close)
        
        self._header_layout.addStretch()
        self._header_layout.addWidget(self._close_btn)
        self._layout.addWidget(self._header)

        # 3. Message log view
        self.chat_log = ChatLog(self)
        self._layout.addWidget(self.chat_log)

        # 4. Collapsible input field
        self.input_field = ChatInputField(self)
        self.input_field.submitted.connect(self._on_input_submitted)
        self.input_field.escaped.connect(self._toggle_input)
        self._layout.addWidget(self.input_field)

        self._show_input = True
        logger.info("Chat Widget UI components built.")

    def _toggle_input(self) -> None:
        self._show_input = not self._show_input
        self.input_field.setVisible(self._show_input)

    def _on_input_submitted(self, text: str) -> None:
        # Append message locally
        self.chat_log.append_message("Bạn", text, is_user=True)
        # Emit signal to Orchestrator
        self.text_submitted.emit(text)
        # Emit to async EventBus
        self._bus.emit_sync(Event(
            type=EventType.USER_TEXT_INPUT,
            data=text,
            source="chat_widget"
        ))

    def append_assistant_response(self, text: str) -> None:
        """Helper to append companion responses to the chat window log."""
        self.chat_log.append_message("Hana", text, is_user=False)

    # Draggable window event handlers
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
