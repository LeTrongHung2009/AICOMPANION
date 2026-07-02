"""
companion/desktop/theme.py
==========================
Premium dark-violet glassmorphism styling parameters for PyQt6 UI components.
"""

from __future__ import annotations

# Stylesheet for main widget
WIDGET_STYLE = """
QWidget#MainWidget {
    background-color: rgba(13, 13, 26, 0.85);
    border: 1px solid rgba(167, 139, 250, 0.25);
    border-radius: 12px;
}
"""

# HTML Template for chat log messages
CHAT_MESSAGE_TEMPLATE = """
<div style="margin-bottom: 8px;">
    <span style="color: {color}; font-weight: bold; font-family: 'Noto Sans'; font-size: 11px;">{sender}:</span>
    <span style="color: #e2e8f0; font-family: 'Noto Sans'; font-size: 11px; line-height: 1.3;"> {text}</span>
</div>
"""

# Input field QSS style
INPUT_STYLE = """
QLineEdit {
    background-color: rgba(26, 26, 46, 0.9);
    border: 1px solid rgba(167, 139, 250, 0.4);
    border-radius: 6px;
    padding: 6px 10px;
    color: #e2e8f0;
    font-family: 'Noto Sans';
    font-size: 11px;
}
QLineEdit:focus {
    border: 1px solid rgba(167, 139, 250, 0.8);
}
"""

# Scroll bar configuration for chat log
SCROLLBAR_STYLE = """
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(167, 139, 250, 0.4);
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(167, 139, 250, 0.7);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
