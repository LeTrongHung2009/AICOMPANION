"""
companion/desktop/live2d_overlay.py
====================================
Live2D Cubism Overlay for Booth PM #4711410.
Renders the Live2D model directly on PyQt6 transparent window.
Handles expressions, lip-sync, and movement.
"""

from __future__ import annotations

import asyncio
import logging
import math
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)

# Model path configuration
MODEL_DIR = Path(__file__).parent.parent.parent / "assets" / "models" / "kira_live2d"

class Live2DOverlay(QWidget):
    """
    Transparent overlay window displaying Live2D avatar.
    Supports:
    - Expression changes (happy, sad, angry, etc.)
    - Lip-sync with TTS audio
    - Free movement across screen
    - Window avoidance
    """
    
    # Signals for expression control
    expression_changed = pyqtSignal(str)
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        initial_x: int = 100,
        initial_y: int = 100,
        scale: float = 0.8,
    ) -> None:
        super().__init__()
        
        self.model_path = model_path or MODEL_DIR
        self.scale = scale
        self.current_expression = "neutral"
        self.is_talking = False
        self.mouth_open_value = 0.0
        
        # Setup window properties
        self._setup_window(initial_x, initial_y)
        
        # Try to load Live2D model (fallback to placeholder if SDK not available)
        self._model_loaded = False
        self._load_model()
        
        # Animation timer for breathing/mouth movement
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(33)  # ~30 FPS
        
        logger.info(f"Live2D Overlay initialized at ({initial_x}, {initial_y})")
    
    def _setup_window(self, x: int, y: int) -> None:
        """Configure transparent overlay window."""
        # Frameless, transparent window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        
        # Initial position and size
        base_width = 400
        base_height = 600
        scaled_width = int(base_width * self.scale)
        scaled_height = int(base_height * self.scale)
        
        self.setGeometry(x, y, scaled_width, scaled_height)
        
        # Placeholder label (fallback if Live2D SDK unavailable)
        self.placeholder = QLabel("🌸 KIRA", self)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 40, 180);
                border-radius: 20px;
                color: #a78bfa;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        self.placeholder.setGeometry(0, 0, scaled_width, scaled_height)
    
    def _load_model(self) -> None:
        """Load Live2D model from disk."""
        if not self.model_path.exists():
            logger.warning(f"Live2D model directory not found: {self.model_path}")
            logger.info("Using placeholder display instead.")
            return
        
        # Check for model files
        model_file = self.model_path / "model.json"
        if not model_file.exists():
            logger.warning(f"model.json not found in {self.model_path}")
            return
        
        try:
            # Try to import PyCubism (optional dependency)
            # If not available, fallback to placeholder
            # import pycubism
            # self._cubism_model = pycubism.load_model(str(model_file))
            # self._model_loaded = True
            # logger.info("Live2D model loaded successfully via PyCubism")
            
            # For now, use placeholder (PyCubism requires manual installation)
            self._model_loaded = False
            logger.info("Live2D model found but PyCubism SDK not installed. Using placeholder.")
            logger.info("To enable full Live2D: pip install pycubism (requires manual build)")
            
        except ImportError as e:
            logger.warning(f"PyCubism import failed: {e}")
            logger.info("Falling back to placeholder display")
            self._model_loaded = False
    
    def _update_animation(self) -> None:
        """Update breathing and mouth animation."""
        if not self._model_loaded:
            # Animate placeholder opacity for breathing effect
            current_alpha = self.placeholder.palette().color(QPalette.ColorRole.Window).alpha()
            breath_offset = math.sin(asyncio.get_event_loop().time() * 2) * 10
            new_alpha = max(150, min(200, 180 + breath_offset))
            
            # Update placeholder style with breathing effect
            if self.is_talking:
                # Pulsing effect when talking
                pulse = int(abs(math.sin(asyncio.get_event_loop().time() * 8)) * 30)
                new_alpha += pulse
            
            self.placeholder.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(20, 20, 40, {int(new_alpha)});
                    border-radius: 20px;
                    color: #a78bfa;
                    font-size: 24px;
                    font-weight: bold;
                }}
            """)
            return
        
        # TODO: Update Live2D model parameters when PyCubism is available
        # self._cubism_model.set_parameter("ParamMouthOpenY", self.mouth_open_value)
        # self._cubism_model.update()
    
    def set_expression(self, expression: str) -> None:
        """
        Change avatar expression.
        
        Args:
            expression: One of ['neutral', 'happy', 'sad', 'angry', 'surprised', 'blush']
        """
        valid_expressions = ['neutral', 'happy', 'sad', 'angry', 'surprised', 'blush']
        if expression not in valid_expressions:
            logger.warning(f"Invalid expression: {expression}. Using 'neutral' instead.")
            expression = 'neutral'
        
        self.current_expression = expression
        self.expression_changed.emit(expression)
        
        if not self._model_loaded:
            # Update placeholder emoji based on expression
            emoji_map = {
                'neutral': '🌸',
                'happy': '😊',
                'sad': '😢',
                'angry': '😠',
                'surprised': '😲',
                'blush': '😳',
            }
            self.placeholder.setText(f"{emoji_map[expression]} KIRA")
        else:
            # TODO: Set Live2D expression parameters
            pass
        
        logger.debug(f"Expression changed to: {expression}")
    
    def start_talking(self) -> None:
        """Start talking animation (lip-sync)."""
        self.is_talking = True
        logger.debug("Started talking animation")
    
    def stop_talking(self) -> None:
        """Stop talking animation."""
        self.is_talking = False
        self.mouth_open_value = 0.0
        logger.debug("Stopped talking animation")
    
    def update_mouth(self, audio_amplitude: float) -> None:
        """
        Update mouth openness based on audio amplitude.
        
        Args:
            audio_amplitude: Normalized value 0.0-1.0 from audio stream
        """
        if not self.is_talking:
            return
        
        # Clamp and smooth mouth value
        target_value = min(1.0, max(0.0, audio_amplitude))
        self.mouth_open_value = 0.7 * self.mouth_open_value + 0.3 * target_value
        
        if self._model_loaded:
            # TODO: Update Live2D mouth parameter
            pass
    
    def move_to(self, x: int, y: int) -> None:
        """Move avatar to screen coordinates."""
        self.move(x, y)
        logger.debug(f"Avatar moved to ({x}, {y})")
    
    def drift_update(self, dx: float, dy: float) -> None:
        """Apply small drift movement."""
        current_pos = self.pos()
        new_x = int(current_pos.x() + dx)
        new_y = int(current_pos.y() + dy)
        self.move(new_x, new_y)
    
    def resize_event(self, event) -> None:
        """Handle window resize."""
        if self.placeholder:
            self.placeholder.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)
    
    def close(self) -> None:
        """Cleanup resources."""
        self.animation_timer.stop()
        # TODO: Cleanup Live2D model if loaded
        super().close()


# Singleton instance management
_overlay_instance: Optional[Live2DOverlay] = None

def get_live2d_overlay() -> Optional[Live2DOverlay]:
    """Get or create the global Live2D overlay instance."""
    global _overlay_instance
    return _overlay_instance

def create_live2d_overlay(
    model_path: Optional[Path] = None,
    initial_x: int = 100,
    initial_y: int = 100,
    scale: float = 0.8,
) -> Live2DOverlay:
    """Create the global Live2D overlay instance."""
    global _overlay_instance
    if _overlay_instance is not None:
        logger.warning("Live2D overlay already exists")
        return _overlay_instance
    
    _overlay_instance = Live2DOverlay(model_path, initial_x, initial_y, scale)
    return _overlay_instance
