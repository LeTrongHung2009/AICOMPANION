"""
companion/expression/expression_engine.py
=========================================
Expression Engine.
Manages websocket connection to VTube Studio API public port.
Handles Handshake, Plugin Registration, sending hotkeys and custom parameters.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import websockets

from companion.expression.vts_expression_map import VTSExpressionMapper
from companion.expression.gesture_controller import GestureController
from companion.utils.event_bus import get_event_bus, EventType, Event
from companion.model_setup.vts_config import VTS_APP_INFO

logger = logging.getLogger(__name__)

class ExpressionEngine:
    """
    Asynchronous VTube Studio integration client.
    Runs a connection loop with auto-reconnect.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8001) -> None:
        self.url = f"ws://{host}:{port}"
        self.gesture_ctrl = GestureController()
        self._bus = get_event_bus()
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._authenticated = False
        self._auth_token = VTS_APP_INFO["authenticationToken"]
        self._task: Optional[asyncio.Task] = None
        
        # Subscribe to mood changed event
        self._bus.subscribe(EventType.MOOD_CHANGED, self._on_mood_changed)
        self._bus.subscribe(EventType.TTS_START, self._on_tts_start)
        self._bus.subscribe(EventType.TTS_END, self._on_tts_end)

    async def start(self) -> None:
        """Start the VTS WebSocket connector loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._connect_loop(), name="vts_connector")
        logger.info(f"VTS Expression Engine started targeting {self.url}")

    async def stop(self) -> None:
        """Stop the engine and close connection."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
        logger.info("VTS Expression Engine stopped")

    async def _connect_loop(self) -> None:
        while self._running:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    logger.info("VTS WebSocket connection established.")
                    await self._bus.publish(Event(EventType.VTS_CONNECTED, source="vts_engine"))
                    
                    # Run authentication / handshake
                    await self._authenticate()
                    
                    # Launch parameter updates sender and messages reader concurrently
                    await asyncio.gather(
                        self._send_updates_loop(),
                        self._read_responses_loop()
                    )
            except websockets.exceptions.ConnectionClosed:
                logger.warning("VTS WebSocket closed. Reconnecting...")
            except Exception as exc:
                logger.error(f"VTS WebSocket connection error: {exc}")
            
            self._authenticated = False
            await self._bus.publish(Event(EventType.VTS_DISCONNECTED, source="vts_engine"))
            await asyncio.sleep(5.0)  # Reconnect delay

    async def _send_json(self, message_type: str, data: dict, request_id: str = "req") -> None:
        if not self._ws:
            return
        payload = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "messageType": message_type,
            "requestId": request_id,
            "data": data
        }
        await self._ws.send(json.dumps(payload))

    async def _authenticate(self) -> None:
        """Handshake authentication flow."""
        # 1. Request token if empty
        if not self._auth_token:
            logger.info("Requesting VTS plugin registration token (Please click Allow in VTS popup)...")
            await self._send_json("AuthenticationTokenRequest", {
                "pluginName": VTS_APP_INFO["pluginName"],
                "pluginDeveloper": VTS_APP_INFO["pluginDeveloper"]
            }, "token_req")
            
            # Token will be received in response loop and saved
            while not self._auth_token and self._running:
                await asyncio.sleep(0.5)

        # 2. Use token to authenticate
        if self._auth_token:
            await self._send_json("AuthenticationRequest", {
                "pluginName": VTS_APP_INFO["pluginName"],
                "pluginDeveloper": VTS_APP_INFO["pluginDeveloper"],
                "authenticationToken": self._auth_token
            }, "auth_req")

    async def _read_responses_loop(self) -> None:
        if not self._ws:
            return
        async for msg in self._ws:
            try:
                data = json.loads(msg)
                msg_type = data.get("messageType")
                req_id = data.get("requestId")
                resp_data = data.get("data", {})

                if msg_type == "AuthenticationTokenResponse":
                    self._auth_token = resp_data.get("authenticationToken", "")
                    logger.info("VTS Authentication Token successfully received!")
                elif msg_type == "AuthenticationResponse":
                    if resp_data.get("authenticated", False):
                        self._authenticated = True
                        logger.info("VTS plugin authenticated successfully!")
                    else:
                        logger.error("VTS authentication failed. Clearing token.")
                        self._auth_token = ""
            except Exception as exc:
                logger.error(f"Error parsing VTS response: {exc}")

    async def _send_updates_loop(self) -> None:
        """Sends periodic coordinate/motion parameters to VTube Studio."""
        while self._running and self._ws:
            if self._authenticated:
                try:
                    # Gather dynamic parameters (breathing, eye blinking, look drift)
                    params = self.gesture_ctrl.calculate_gestures()
                    
                    # Convert to VTS injection format
                    vts_params = []
                    for k, v in params.items():
                        vts_params.append({
                            "id": k,
                            "value": v,
                            "weight": 1.0
                        })

                    await self._send_json("InjectParameterDataRequest", {
                        "faceFound": True,
                        "mode": "set",
                        "parameterValues": vts_params
                    }, "param_inject")
                except Exception as exc:
                    logger.error(f"VTS Parameter injection error: {exc}")
            
            # Send at 40 Hz (25ms sleep)
            await asyncio.sleep(0.025)

    async def _on_mood_changed(self, event: Event) -> None:
        """React to emotional state adjustments by triggering expression hotkeys."""
        if not self._authenticated:
            return
        mood_state = event.data
        hotkey, is_reset = VTSExpressionMapper.map_mood_to_hotkey(mood_state)
        
        try:
            logger.info(f"Sending VTS hotkey trigger: {hotkey}")
            await self._send_json("HotkeyTriggerRequest", {
                "hotkeyID": hotkey
            }, "hotkey_trigger")
        except Exception as exc:
            logger.error(f"Failed to trigger VTS expression: {exc}")

    async def _on_tts_start(self, event: Event) -> None:
        """Trigger talking animation parameters on TTS output start."""
        # Simple mouth open simulation
        # For a full integration, you can stream mock audio mouth capture parameters
        pass

    async def _on_tts_end(self, event: Event) -> None:
        pass
