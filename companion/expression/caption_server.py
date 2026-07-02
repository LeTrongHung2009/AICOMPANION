"""
companion/expression/caption_server.py
======================================
Caption Server.
Runs a local WebSocket server (default 127.0.0.1:8765) to broadcast
word-by-word or line-by-line subtitles to OBS Studio browser sources.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set, Optional
import websockets

logger = logging.getLogger(__name__)

class CaptionServer:
    """
    Sub-server broadcasting subtitles for OBS browser sources.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self._server = None

    async def start(self) -> None:
        """Start the WebSocket server."""
        try:
            self._server = await websockets.serve(
                self._register_handler,
                self.host,
                self.port
            )
            logger.info(f"Caption WebSocket Server active at ws://{self.host}:{self.port}")
        except Exception as exc:
            logger.error(f"Failed to start Caption Server: {exc}")

    async def stop(self) -> None:
        """Stop the server and close active client connections."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for client in list(self.clients):
            await client.close()
        logger.info("Caption Server stopped.")

    async def _register_handler(self, websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        self.clients.add(websocket)
        logger.info(f"OBS Caption source connected from {websocket.remote_address}")
        try:
            async for _ in websocket:
                pass  # Keep connection open, client only listens
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            logger.info(f"OBS Caption source disconnected.")

    async def broadcast_caption(self, text: str, is_user: bool = False) -> None:
        """
        Broadcast a new subtitle line.
        
        Args:
            text: Subtitle text string.
            is_user: True if subtitle belongs to User, False for Hana.
        """
        if not self.clients:
            return

        payload = json.dumps({
            "type": "caption",
            "text": text,
            "speaker": "user" if is_user else "hana",
            "timestamp": asyncio.get_event_loop().time()
        })

        # Broadcast asynchronously to all connected browser sources
        tasks = [asyncio.create_task(client.send(payload)) for client in self.clients]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug(f"Broadcasted caption to {len(tasks)} clients: '{text[:40]}…'")
