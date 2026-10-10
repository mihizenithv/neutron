"""
NEUTRON WebSocket Handlers

Real-time GUI state broadcasting.
"""

from __future__ import annotations

import asyncio
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config.constants import WSMessageType, STATE_BROADCAST_INTERVAL_MS, SystemEvent
from utils.logging_config import get_logger
from utils.state import get_state
from utils.events import get_event_bus


websocket_router = APIRouter()
logger = get_logger("WebSocket")


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task: asyncio.Task | None = None
        self._running = False
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
        
        if len(self.active_connections) == 1:
            await self.start_broadcast()
        
        # Emit connection event
        event_bus = get_event_bus()
        await event_bus.publish(SystemEvent.CLIENT_CONNECTED, {"client_id": str(id(websocket))})
        
        # Send initial state
        state = get_state()
        await self.send_personal(websocket, {
            "type": WSMessageType.STATE_UPDATE.value,
            "data": state.to_gui_state(),
        })
    
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")
        
        # Stop broadcast if no connections
        if len(self.active_connections) == 0:
            self.stop_broadcast()
    
    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.debug(f"Send error: {e}")
    
    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)
    
    async def start_broadcast(self) -> None:
        """Start state broadcast loop."""
        if self._running:
            return
        
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
    
    def stop_broadcast(self) -> None:
        """Stop broadcast loop."""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None
    
    async def _broadcast_loop(self) -> None:
        """Periodic state broadcast loop."""
        state = get_state()
        interval = STATE_BROADCAST_INTERVAL_MS / 1000
        
        while self._running:
            try:
                await self.broadcast({
                    "type": WSMessageType.STATE_UPDATE.value,
                    "data": state.to_gui_state(),
                })
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                await asyncio.sleep(1)


manager = ConnectionManager()


@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for GUI communication."""
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "type": WSMessageType.ERROR.value,
                    "error": "Invalid JSON",
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, message: dict) -> None:
    """Handle incoming client messages."""
    msg_type = message.get("type", "")
    
    if msg_type == "ping":
        await manager.send_personal(websocket, {"type": "pong"})
    elif msg_type == "get_state":
        state = get_state()
        await manager.send_personal(websocket, {
            "type": WSMessageType.STATE_UPDATE.value,
            "data": state.to_gui_state(),
        })
    else:
        logger.debug(f"Unknown message type: {msg_type}")


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager


__all__ = ["websocket_router", "ConnectionManager", "get_connection_manager"]
