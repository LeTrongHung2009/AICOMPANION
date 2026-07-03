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

# Model path configuration
MODEL_DIR = Path(__file__).parent.parent.parent / "assets" / "models" / "kira_live2d"


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
        
        self.model_path = model_path or MODEL_DIR
        self.scale = scale
        self.current_expression = "neutral"
        self.is_talking = False
        self.mouth_open_value = 0.0
        self._model_loaded = False
        
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
            self._show_placeholder("Model directory not found")
            return
        
        # Check for model.json file
        model_file = self.model_path / "model.json"
        if not model_file.exists():
            logger.warning(f"model.json not found in {self.model_path}")
            self._show_placeholder("model.json not found")
            return
        
        try:
            # Generate HTML content for Live2D rendering
            html_content = self._generate_live2d_html(model_file)
            
            # Load HTML into WebEngine
            self.web_view.setHtml(html_content, QUrl.fromLocalFile(str(self.model_path)))
            
            logger.info(f"Live2D model loaded: {model_file}")
            self._model_loaded = True
            self.model_loaded.emit(True)
            
        except Exception as e:
            logger.error(f"Failed to load Live2D model: {e}")
            self._show_placeholder(f"Error: {str(e)}")
            self._model_loaded = False
            self.model_loaded.emit(False)
    
    def _generate_live2d_html(self, model_file: Path) -> str:
        """Generate HTML page with Live2D Cubism SDK."""
        # Convert Path to string for JSON
        model_json_path = str(model_file.name)
        
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
            background: rgba(20, 20, 40, 0.9);
            padding: 20px 40px;
            border-radius: 10px;
            border: 2px solid #a78bfa;
        }}
        #error-details {{
            font-size: 12px;
            opacity: 0.8;
            margin-top: 10px;
            max-width: 400px;
        }}
    </style>
</head>
<body>
    <div id="canvas-container">
        <canvas id="live2d"></canvas>
    </div>
    <div id="loading">Loading KIRA...</div>
    
    <!-- Live2D Cubism Core (Required for Cubism 4+) -->
    <script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
    
    <!-- Live2D Cubism 4 SDK for Web (R3) -->
    <script src="https://cdn.jsdelivr.net/npm/live2d-cubism-sdk-for-web@4.0.0/dist/live2dcubismframework.min.js"></script>
    
    <script>
        // Global state
        let model = null;
        let canvas = null;
        let gl = null;
        let cubismApp = null;
        let animationFrameId = null;
        let mouthOpen = 0.0;
        let targetMouthOpen = 0.0;
        let time = 0;
        let isModelLoaded = false;
        let parameterIds = {{}};
        
        // Wait for libraries to load with timeout
        let loadAttempts = 0;
        const MAX_LOAD_ATTEMPTS = 50;
        
        function waitForLibraries() {{
            loadAttempts++;
            if (loadAttempts > MAX_LOAD_ATTEMPTS) {{
                showError('Failed to load Live2D libraries. Check internet connection.');
                return;
            }}
            if (typeof Live2DCubismCore === 'undefined') {{
                setTimeout(waitForLibraries, 100);
                return;
            }}
            if (typeof live2d === 'undefined' || typeof live2d.CubismFramework === 'undefined') {{
                setTimeout(waitForLibraries, 100);
                return;
            }}
            initializeLive2D();
        }}
        
        function showError(message) {{
            const loadingEl = document.getElementById('loading');
            loadingEl.innerHTML = '<strong>⚠️ Error</strong><br>' + message;
            loadingEl.style.display = 'block';
            console.error(message);
        }}
        
        function showLoading(message) {{
            const loadingEl = document.getElementById('loading');
            loadingEl.textContent = message;
            loadingEl.style.display = 'block';
        }}
        
        function hideLoading() {{
            const loadingEl = document.getElementById('loading');
            loadingEl.style.display = 'none';
        }}
        
        function initializeLive2D() {{
            try {{
                // Initialize Cubism Framework
                live2d.CubismFramework.startUp();
                live2d.CubismFramework.initialize();
                
                hideLoading();
                
                canvas = document.getElementById('live2d');
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                
                gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
                if (!gl) {{
                    showError('WebGL not supported in this browser');
                    return;
                }}
                
                // Enable transparency with proper blending
                gl.clearColor(0.0, 0.0, 0.0, 0.0);
                gl.enable(gl.BLEND);
                gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
                
                // Load model
                loadModel('{model_json_path}');
            }} catch (e) {{
                showError('Initialization error: ' + e.message);
                console.error(e);
            }}
        }}
        
        function loadModel(modelPath) {{
            showLoading('Loading model data...');
            
            const request = new XMLHttpRequest();
            request.open('GET', modelPath);
            request.responseType = 'json';
            
            request.onload = function() {{
                if (request.status >= 400) {{
                    showError('Failed to load model.json (HTTP ' + request.status + ')');
                    return;
                }}
                
                const modelData = request.response;
                createModel(modelData, modelPath.substring(0, modelPath.lastIndexOf('/')));
            }};
            
            request.onerror = function() {{
                showError('Network error loading model. Check file paths.');
            }};
            
            request.send();
        }}
        
        function loadFile(path, type) {{
            return new Promise((resolve, reject) => {{
                const request = new XMLHttpRequest();
                request.open('GET', path);
                
                if (type === 'arraybuffer') {{
                    request.responseType = 'arraybuffer';
                }} else if (type === 'json') {{
                    request.responseType = 'json';
                }}
                
                request.onload = function() {{
                    if (request.status >= 400) {{
                        reject(new Error('HTTP ' + request.status));
                    }} else {{
                        resolve(request.response);
                    }}
                }};
                
                request.onerror = function() {{
                    reject(new Error('Network error'));
                }};
                
                request.send();
            }});
        }}
        
        async function createModel(modelData, basePath) {{
            try {{
                showLoading('Loading resources...');
                
                // Load Moc file
                const mocPath = basePath + '/' + modelData.FileReferences.Moc;
                const mocArrayBuffer = await loadFile(mocPath, 'arraybuffer');
                const moc = live2d.CubismMoc.fromArrayBuffer(mocArrayBuffer);
                
                if (!moc) {{
                    throw new Error('Failed to load .moc3 file');
                }}
                
                // Load textures
                const texturePaths = modelData.FileReferences.Textures || [];
                const textures = [];
                
                for (let i = 0; i < texturePaths.length; i++) {{
                    showLoading(`Loading texture ${{i+1}}/${{texturePaths.length}}...`);
                    const texPath = basePath + '/' + texturePaths[i];
                    const texArrayBuffer = await loadFile(texPath, 'arraybuffer');
                    
                    const texture = gl.createTexture();
                    gl.bindTexture(gl.TEXTURE_2D, texture);
                    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(texArrayBuffer));
                    gl.generateMipmap(gl.TEXTURE_2D);
                    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_NEAREST);
                    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
                    gl.bindTexture(gl.TEXTURE_2D, null);
                    
                    textures.push(texture);
                }}
                
                // Create model
                model = moc.createModel();
                
                // Setup renderer
                cubismApp = new live2d.CubismUserModel();
                cubismApp.model = model;
                cubismApp.renderer = new live2d.CubismRenderer_WebGL(model);
                cubismApp.renderer.initialize(textures);
                
                // Load motions if available
                if (modelData.FileReferences.Motions) {{
                    // Motions can be loaded here
                    console.log('Motions available:', Object.keys(modelData.FileReferences.Motions));
                }}
                
                // Discover parameter IDs dynamically
                discoverParameters(model);
                
                // Set initial values
                resetModelParameters();
                
                console.log('Live2D model loaded successfully');
                isModelLoaded = true;
                hideLoading();
                
                // Start render loop
                render();
            }} catch (e) {{
                showError('Model creation error: ' + e.message);
                console.error('Full error:', e);
            }}
        }}
        
        function discoverParameters(model) {{
            // Dynamically discover all parameter IDs
            const paramCount = model.parameters.count;
            parameterIds = {{}};
            
            for (let i = 0; i < paramCount; i++) {{
                const id = model.parameters.getId(i);
                const value = model.parameters.getValue(i);
                
                // Store common parameters
                if (id.includes('AngleX')) parameterIds.angleX = id;
                else if (id.includes('AngleY')) parameterIds.angleY = id;
                else if (id.includes('AngleZ')) parameterIds.angleZ = id;
                else if (id.includes('BodyAngleX')) parameterIds.bodyAngleX = id;
                else if (id.includes('EyeBlink')) parameterIds.eyeBlink = id;
                else if (id.includes('EyeL') && id.includes('Open')) parameterIds.eyeLOpen = id;
                else if (id.includes('EyeR') && id.includes('Open')) parameterIds.eyeROpen = id;
                else if (id.includes('Mouth') && id.includes('Open')) parameterIds.mouthOpen = id;
                else if (id.includes('Breath')) parameterIds.breath = id;
                
                console.log(`Parameter ${{i}}: ${{id}} = ${{value}}`);
            }}
            
            console.log('Discovered parameters:', parameterIds);
        }}
        
        function setParameterValue(paramName, value, defaultValue = 0) {{
            if (!model || !isModelLoaded) return;
            
            const id = parameterIds[paramName];
            if (id) {{
                model.setParameterValueById(id, value);
            }} else {{
                // Try to find by common naming patterns
                const paramCount = model.parameters.count;
                for (let i = 0; i < paramCount; i++) {{
                    const pid = model.parameters.getId(i);
                    if (pid.includes(paramName)) {{
                        model.setParameterValueById(pid, value);
                        parameterIds[paramName] = pid;
                        return;
                    }}
                }}
                // Use default if parameter not found
                console.warn(`Parameter '${{paramName}}' not found in this model`);
            }}
        }}
        
        function resetModelParameters() {{
            if (!model) return;
            
            // Reset all angles to neutral
            setParameterValue('angleX', 0);
            setParameterValue('angleY', 0);
            setParameterValue('angleZ', 0);
            setParameterValue('bodyAngleX', 0);
            
            // Set default eye openness
            if (parameterIds.eyeLOpen) {{
                model.setParameterValueById(parameterIds.eyeLOpen, 1.0);
            }}
            if (parameterIds.eyeROpen) {{
                model.setParameterValueById(parameterIds.eyeROpen, 1.0);
            }}
        }}
        
        function render() {{
            if (!model || !isModelLoaded) {{
                animationFrameId = requestAnimationFrame(render);
                return;
            }}
            
            time += 0.016; // ~60fps
            
            // Smooth mouth movement
            mouthOpen += (targetMouthOpen - mouthOpen) * 0.3;
            
            // Breathing animation
            const breath = Math.sin(time * 2) * 0.1;
            setParameterValue('breath', breath);
            
            // Blink animation (every 3-5 seconds randomly)
            const blinkCycle = Math.abs(Math.sin(time * 0.5));
            const isBlinking = blinkCycle > 0.95;
            const eyeOpenValue = isBlinking ? 0.0 : 1.0;
            
            if (parameterIds.eyeLOpen) {{
                model.setParameterValueById(parameterIds.eyeLOpen, eyeOpenValue);
            }}
            if (parameterIds.eyeROpen) {{
                model.setParameterValueById(parameterIds.eyeROpen, eyeOpenValue);
            }}
            
            // Apply mouth openness for lip-sync
            setParameterValue('mouthOpen', mouthOpen);
            
            // Update and draw
            model.update();
            cubismApp.renderer.draw();
            
            animationFrameId = requestAnimationFrame(render);
        }}
        
        // Handle window resize
        window.addEventListener('resize', () => {{
            if (canvas) {{
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                gl.viewport(0, 0, canvas.width, canvas.height);
            }}
        }});
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {{
            if (animationFrameId) {{
                cancelAnimationFrame(animationFrameId);
            }}
            if (cubismApp && cubismApp.renderer) {{
                cubismApp.renderer.release();
            }}
            if (live2d.CubismFramework) {{
                live2d.CubismFramework.dispose();
            }}
        }});
        
        // Expose functions for Python to call
        window.setExpression = function(expr) {{
            if (!model || !isModelLoaded) {{
                console.warn('Model not loaded yet');
                return;
            }}
            console.log('Setting expression:', expr);
            
            // Expression mapping - adjust based on model's actual parameters
            const expressions = {{
                'neutral': {{ eyeScale: 1.0, mouthY: 0 }},
                'happy': {{ eyeScale: 1.2, mouthY: 0.3 }},
                'sad': {{ eyeScale: 0.8, mouthY: -0.2 }},
                'angry': {{ eyeScale: 0.9, mouthY: -0.1 }},
                'surprised': {{ eyeScale: 1.5, mouthY: 0.5 }},
                'blush': {{ eyeScale: 1.0, mouthY: 0.1 }}
            }};
            
            const exp = expressions[expr] || expressions['neutral'];
            
            // Apply eye scale
            if (parameterIds.eyeLOpen) {{
                model.setParameterValueById(parameterIds.eyeLOpen, exp.eyeScale);
            }}
            if (parameterIds.eyeROpen) {{
                model.setParameterValueById(parameterIds.eyeROpen, exp.eyeScale);
            }}
            
            // Apply mouth
            if (parameterIds.mouthOpen) {{
                model.setParameterValueById(parameterIds.mouthOpen, exp.mouthY);
            }}
        }};
        
        window.setMouthOpen = function(value) {{
            targetMouthOpen = Math.max(0, Math.min(1, value));
        }};
        
        window.setModelAngle = function(x, y, z) {{
            if (!model || !isModelLoaded) return;
            setParameterValue('angleX', x);
            setParameterValue('angleY', y);
            setParameterValue('angleZ', z);
        }};
        
        window.isModelReady = function() {{
            return isModelLoaded;
        }};
        
        // Auto-start initialization
        waitForLibraries();
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
