"""
companion/desktop/live2d_overlay.py
====================================
Live2D Cubism Overlay for Booth PM #4711410.
Renders the Live2D model via PyQt6-WebEngine using WebGL.
Handles expressions, lip-sync, and movement.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings

logger = logging.getLogger(__name__)

# Model path configuration - Use absolute path from project root
MODEL_DIR = Path(__file__).parent.parent.parent / "assets" / "models" / "kira_live2d"

# Fallback paths to check
FALLBACK_MODEL_PATHS = [
    Path(__file__).parent.parent.parent / "assets" / "models" / "kira_live2d",
    Path.home() / ".kira_companion" / "models" / "kira_live2d",
    Path("/usr/share/kira/models"),
]


class Live2DWebPage(QWebEnginePage):
    """Custom WebEngine page with console logging enabled."""
    
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        """Capture JS console messages for debugging."""
        js_level = {
            0: "DEBUG",
            1: "INFO", 
            2: "WARNING",
            3: "ERROR"
        }.get(level, "LOG")
        logger.debug(f"[JS {js_level}] {source_id}:{line_number} - {message}")


class Live2DOverlay(QWidget):
    """
    Transparent overlay window displaying Live2D avatar via WebEngine.
    Supports:
    - Expression changes (happy, sad, angry, etc.)
    - Lip-sync with TTS audio
    - Free movement across screen
    - Window avoidance
    """
    
    # Signals for expression control
    expression_changed = pyqtSignal(str)
    model_loaded = pyqtSignal(bool)
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        initial_x: int = 100,
        initial_y: int = 100,
        scale: float = 0.8,
    ) -> None:
        super().__init__()
        
        # Try provided path first, then fallback paths
        if model_path:
            self.model_path = model_path
        else:
            self.model_path = MODEL_DIR
            # Check fallback paths if main path doesn't exist
            if not self.model_path.exists():
                for fallback in FALLBACK_MODEL_PATHS[1:]:  # Skip first since it's the same as MODEL_DIR
                    if fallback.exists():
                        logger.info(f"Using fallback model path: {fallback}")
                        self.model_path = fallback
                        break
        
        self.scale = scale
        self.current_expression = "neutral"
        self.is_talking = False
        self.mouth_open_value = 0.0
        self._model_loaded = False
        
        # Debug: Log model path info
        logger.info(f"Live2DOverlay initializing with model_path: {self.model_path}")
        logger.info(f"Model path exists: {self.model_path.exists()}")
        if self.model_path.exists():
            files = list(self.model_path.iterdir())
            logger.info(f"Model directory contents: {[f.name for f in files]}")
        
        # Setup window properties
        self._setup_window(initial_x, initial_y)
        
        # Setup WebEngine view for Live2D rendering
        self._setup_webengine()
        
        # Load Live2D model
        self._load_model()
        
        # Animation timer for breathing/mouth movement
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(33)  # ~30 FPS
        
        logger.info(f"Live2D Overlay initialized at ({initial_x}, {initial_y})")
    
    def _setup_window(self, x: int, y: int) -> None:
        """Configure transparent overlay window."""
        # Frameless, transparent window that stays on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_X11DoNotAcceptFocus, True)
        
        # Initial position and size
        base_width = 400
        base_height = 600
        scaled_width = int(base_width * self.scale)
        scaled_height = int(base_height * self.scale)
        
        self.setGeometry(x, y, scaled_width, scaled_height)
        self.setMinimumSize(QSize(200, 300))
    
    def _setup_webengine(self) -> None:
        """Setup QWebEngineView for Live2D rendering."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create WebEngine view
        self.web_view = QWebEngineView(self)
        self.web_view.setPage(Live2DWebPage(self.web_view))
        
        # Configure WebEngine settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        
        # Make web view background transparent
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent;")
        
        layout.addWidget(self.web_view)
        self.setLayout(layout)
    
    def _load_model(self) -> None:
        """Load Live2D model from disk and render via WebEngine."""
        if not self.model_path.exists():
            logger.warning(f"Live2D model directory not found: {self.model_path}")
            logger.warning("Please download model from: https://booth.pm/jp/items/4711410")
            logger.warning(f"Expected path: {self.model_path}")
            self._show_placeholder("Model directory not found\nDownload from booth.pm/jp/items/4711410")
            return
        
        # Check for model.json file
        model_file = self.model_path / "model.json"
        if not model_file.exists():
            logger.warning(f"model.json not found in {self.model_path}")
            logger.warning(f"Files in directory: {[f.name for f in self.model_path.iterdir()]}")
            self._show_placeholder("model.json not found\nCheck assets/models/kira_live2d/")
            return
        
        try:
            # Generate HTML content for Live2D rendering
            html_content = self._generate_live2d_html(model_file)
            
            # Load HTML into WebEngine with proper base URL for local file access
            base_url = QUrl.fromLocalFile(str(self.model_path.absolute()))
            logger.info(f"Loading HTML with base URL: {base_url}")
            logger.info(f"Model file path: {model_file}")
            
            self.web_view.setHtml(html_content, base_url)
            
            logger.info(f"Live2D model HTML loaded: {model_file}")
            self._model_loaded = True
            self.model_loaded.emit(True)
            
        except Exception as e:
            logger.error(f"Failed to load Live2D model: {e}", exc_info=True)
            self._show_placeholder(f"Error loading model:\n{str(e)}")
            self._model_loaded = False
            self.model_loaded.emit(False)
    
    def _generate_live2d_html(self, model_file: Path) -> str:
        """Generate HTML page with Live2D Cubism SDK."""
        # Convert Path to string for JSON
        model_json_path = str(model_file.name)
        
        # Get absolute path for base URL
        model_dir_url = QUrl.fromLocalFile(str(self.model_path.absolute())).toString()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KIRA Live2D</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            background: transparent;
            overflow: hidden;
            width: 100vw;
            height: 100vh;
        }}
        #canvas-container {{
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        canvas {{
            max-width: 100%;
            max-height: 100%;
        }}
        #loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #a78bfa;
            font-family: Arial, sans-serif;
            font-size: 18px;
            text-align: center;
        }}
        #error-message {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #ff6b6b;
            font-family: Arial, sans-serif;
            font-size: 14px;
            text-align: center;
            max-width: 80%;
            display: none;
        }}
    </style>
</head>
<body>
    <div id="canvas-container">
        <canvas id="live2d"></canvas>
    </div>
    <div id="loading">Loading KIRA...</div>
    <div id="error-message"></div>
    
    <!-- Live2D Cubism Core (REQUIRED - must load first) -->
    <script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
    
    <!-- PIXI.js (Required for rendering) -->
    <script src="https://cdn.jsdelivr.net/npm/pixi.js@7.3.2/dist/browser/pixi.min.js"></script>
    
    <!-- pixi-live2d-display wrapper (easier API) -->
    <script src="https://cdn.jsdelivr.net/npm/pixi-live2d-display@0.4.0/dist/index.min.js"></script>
    
    <script>
        console.log('[Live2D] Starting initialization...');
        console.log('[Live2D] Model directory:', '{model_dir_url}');
        console.log('[Live2D] Model file:', '{model_json_path}');
        
        let app = null;
        let currentModel = null;
        
        // Show error helper
        function showError(msg) {{
            const el = document.getElementById('error-message');
            el.textContent = 'Error: ' + msg;
            el.style.display = 'block';
            document.getElementById('loading').style.display = 'none';
            console.error('[Live2D]', msg);
        }}
        
        // Wait for all libraries to load
        function waitForLibraries() {{
            if (typeof PIXI === 'undefined') {{
                console.log('[Live2D] Waiting for PIXI...');
                setTimeout(waitForLibraries, 100);
                return;
            }}
            if (typeof Live2DCubismCore === 'undefined' && typeof cubismCore === 'undefined') {{
                console.log('[Live2D] Waiting for Cubism Core...');
                setTimeout(waitForLibraries, 100);
                return;
            }}
            if (!PIXI.live2d || !PIXI.live2d.Live2DModel) {{
                console.log('[Live2D] Waiting for pixi-live2d-display...');
                setTimeout(waitForLibraries, 100);
                return;
            }}
            console.log('[Live2D] All libraries loaded, initializing...');
            initializeLive2D();
        }}
        
        async function initializeLive2D() {{
            try {{
                const canvas = document.getElementById('live2d');
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                
                console.log('[Live2D] Canvas size:', canvas.width, 'x', canvas.height);
                document.getElementById('loading').textContent = 'Initializing WebGL...';
                
                // Create PIXI Application with transparent background
                app = new PIXI.Application({{
                    view: canvas,
                    width: canvas.width,
                    height: canvas.height,
                    transparent: true,
                    backgroundColor: 0x00000000,
                    backgroundAlpha: 0,
                    autoStart: true,
                    resolution: window.devicePixelRatio || 1,
                    autoDensity: true,
                    antialias: true,
                    preserveDrawingBuffer: true
                }});
                
                console.log('[Live2D] PIXI application created');
                console.log('[Live2D] PIXI version:', PIXI.VERSION);
                console.log('[Live2D] Cubism core available:', typeof Live2DCubismCore !== 'undefined' || typeof cubismCore !== 'undefined');
                
                document.getElementById('loading').textContent = 'Loading model from {model_json_path}...';
                
                // Load model using pixi-live2d-display
                const modelUrl = '{model_dir_url}{model_json_path}';
                console.log('[Live2D] Loading model from:', modelUrl);
                
                currentModel = await PIXI.live2d.Live2DModel.from(modelUrl, {{
                    autoInteract: false,
                    draggable: false,
                    hitAreaScale: 1.0,
                    mouseTracking: false,
                    autoFocus: false
                }});
                
                console.log('[Live2D] Model loaded successfully!');
                console.log('[Live2D] Model internal:', currentModel.internalModel);
                
                // Add model to stage
                app.stage.addChild(currentModel);
                
                // Center and scale model
                const scaleX = (app.screen.width * 0.8) / currentModel.width;
                const scaleY = (app.screen.height * 0.8) / currentModel.height;
                const scale = Math.min(scaleX, scaleY);
                
                currentModel.scale.set(scale);
                currentModel.x = (app.screen.width - currentModel.width) / 2;
                currentModel.y = (app.screen.height - currentModel.height) / 2;
                
                console.log('[Live2D] Model positioned at:', currentModel.x, currentModel.y, 'scale:', scale);
                
                // Hide loading message
                document.getElementById('loading').style.display = 'none';
                
                // Setup expression functions
                setupFunctions();
                
            }} catch (e) {{
                console.error('[Live2D] Initialization error:', e);
                console.error('[Live2D] Stack:', e.stack);
                showError(e.message || 'Unknown error loading model');
            }}
        }}
        
        function setupFunctions() {{
            console.log('[Live2D] Setting up control functions...');
            
            // Expose functions for Python to call
            window.setExpression = function(expr) {{
                console.log('[Live2D] Setting expression:', expr);
                if (!currentModel || !currentModel.internalModel) {{
                    console.warn('[Live2D] Model not ready');
                    return;
                }}
                
                const coreModel = currentModel.internalModel.coreModel;
                if (!coreModel) {{
                    console.warn('[Live2D] Core model not available');
                    return;
                }}
                
                // Set basic parameters based on expression
                const expressions = {{
                    'neutral': {{ eye: 1.0, mouth: 0.0, brow: 0.0 }},
                    'happy': {{ eye: 1.2, mouth: 0.3, brow: 0.2 }},
                    'sad': {{ eye: 0.8, mouth: -0.2, brow: -0.3 }},
                    'angry': {{ eye: 0.9, mouth: -0.1, brow: -0.5 }},
                    'surprised': {{ eye: 1.5, mouth: 0.5, brow: 0.4 }},
                    'blush': {{ eye: 1.0, mouth: 0.1, brow: 0.1 }}
                }};
                
                const exp = expressions[expr] || expressions['neutral'];
                
                try {{
                    // Try different parameter names (Cubism 3 vs 4)
                    const paramNames = {{
                        eye: ['ParamEyeLOpen', 'PARAM_EYE_L_OPEN'],
                        mouth: ['ParamMouthOpenY', 'PARAM_MOUTH_OPEN_Y'],
                        brow: ['ParamBrowLY', 'PARAM_BROW_LY']
                    }};
                    
                    for (const [key, value] of Object.entries(exp)) {{
                        for (const paramName of paramNames[key]) {{
                            if (coreModel.getParameterId) {{
                                const id = coreModel.getParameterId(paramName);
                                if (id !== undefined) {{
                                    coreModel.setParameterValueById(id, value);
                                    break;
                                }}
                            }} else if (coreModel.setParameterValue) {{
                                coreModel.setParameterValue(paramName, value);
                                break;
                            }}
                        }}
                    }}
                    console.log('[Live2D] Expression set successfully');
                }} catch (e) {{
                    console.error('[Live2D] Error setting expression:', e);
                }}
            }};
            
            window.setMouthOpen = function(value) {{
                if (!currentModel || !currentModel.internalModel) return;
                
                const coreModel = currentModel.internalModel.coreModel;
                if (!coreModel) return;
                
                try {{
                    if (coreModel.getParameterId) {{
                        const id = coreModel.getParameterId('ParamMouthOpenY');
                        if (id !== undefined) {{
                            coreModel.setParameterValueById(id, value);
                        }}
                    }} else if (coreModel.setParameterValue) {{
                        coreModel.setParameterValue('ParamMouthOpenY', value);
                    }}
                }} catch (e) {{
                    console.error('[Live2D] Error setting mouth:', e);
                }}
            }};
            
            window.setModelAngle = function(x, y, z) {{
                if (!currentModel || !currentModel.internalModel) return;
                
                const coreModel = currentModel.internalModel.coreModel;
                if (!coreModel) return;
                
                try {{
                    const params = {{
                        x: ['ParamAngleX', 'PARAM_ANGLE_X'],
                        y: ['ParamAngleY', 'PARAM_ANGLE_Y'],
                        z: ['ParamAngleZ', 'PARAM_ANGLE_Z']
                    }};
                    
                    for (const [axis, value] of Object.entries({{x, y, z}})) {{
                        for (const paramName of params[axis]) {{
                            if (coreModel.getParameterId) {{
                                const id = coreModel.getParameterId(paramName);
                                if (id !== undefined) {{
                                    coreModel.setParameterValueById(id, value);
                                    break;
                                }}
                            }} else if (coreModel.setParameterValue) {{
                                coreModel.setParameterValue(paramName, value);
                                break;
                            }}
                        }}
                    }}
                }} catch (e) {{
                    console.error('[Live2D] Error setting angle:', e);
                }}
            }};
            
            console.log('[Live2D] Control functions ready');
        }}
        
        // Handle window resize
        window.addEventListener('resize', () => {{
            if (app) {{
                app.renderer.resize(window.innerWidth, window.innerHeight);
                if (currentModel) {{
                    currentModel.x = (app.screen.width - currentModel.width) / 2;
                    currentModel.y = (app.screen.height - currentModel.height) / 2;
                }}
            }}
        }});
        
        // Auto-start initialization
        console.log('[Live2D] Starting library detection...');
        waitForLibraries();
        
        // Timeout after 10 seconds
        setTimeout(() => {{
            if (!currentModel) {{
                showError('Timeout: Model failed to load after 10s. Check network connection and model files.');
            }}
        }}, 10000);
    </script>
</body>
</html>"""
        return html
    
    def _show_placeholder(self, message: str) -> None:
        """Show placeholder when model cannot be loaded."""
        placeholder_html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            background: transparent;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            font-family: Arial, sans-serif;
        }}
        .placeholder {{
            background: rgba(20, 20, 40, 0.8);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            color: #a78bfa;
            font-size: 24px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="placeholder">
        🌸 KIRA<br>
        <span style="font-size: 14px; opacity: 0.8;">{message}</span>
    </div>
</body>
</html>"""
        self.web_view.setHtml(placeholder_html)
        self._model_loaded = False
    
    def _update_animation(self) -> None:
        """Update breathing and mouth animation."""
        if not self._model_loaded:
            return
        
        # Breathing animation
        breath_value = math.sin(asyncio.get_event_loop().time() * 2) * 0.1
        
        # Apply mouth openness if talking
        if self.is_talking:
            # Smooth mouth movement
            target = self.mouth_open_value
            self.mouth_open_value = 0.7 * self.mouth_open_value + 0.3 * target
            
            # Call JS to update mouth
            self.web_view.page().runJavaScript(
                f"window.setMouthOpen({self.mouth_open_value})"
            )
    
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
        
        if self._model_loaded:
            # Call JS to change expression
            self.web_view.page().runJavaScript(
                f"window.setExpression('{expression}')"
            )
        
        logger.debug(f"Expression changed to: {expression}")
    
    def start_talking(self) -> None:
        """Start talking animation (lip-sync)."""
        self.is_talking = True
        logger.debug("Started talking animation")
    
    def stop_talking(self) -> None:
        """Stop talking animation."""
        self.is_talking = False
        self.mouth_open_value = 0.0
        if self._model_loaded:
            self.web_view.page().runJavaScript("window.setMouthOpen(0.0)")
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
        self.mouth_open_value = target_value
        
        if self._model_loaded:
            self.web_view.page().runJavaScript(
                f"window.setMouthOpen({target_value})"
            )
    
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
    
    def resizeEvent(self, event) -> None:
        """Handle window resize."""
        if self.web_view:
            self.web_view.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)
    
    def closeEvent(self, event) -> None:
        """Cleanup resources."""
        self.animation_timer.stop()
        if self.web_view:
            self.web_view.close()
        logger.info("Live2D Overlay closed")
        super().closeEvent(event)


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
