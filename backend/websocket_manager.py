"""WebSocket connection manager for live updates."""
from fastapi import WebSocket
from typing import List, Dict, Any
import json
import asyncio


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def send_step_update(self, step_data: dict):
        await self.broadcast({"type": "step_update", "data": step_data})

    async def send_log(self, level: str, message: str, step: str = ""):
        await self.broadcast({
            "type": "log",
            "data": {"level": level, "message": message, "step": step}
        })

    async def send_response_chunk(self, chunk: str):
        await self.broadcast({"type": "response_chunk", "data": {"chunk": chunk}})

    async def send_plan(self, plan_data: dict):
        await self.broadcast({"type": "plan", "data": plan_data})

    async def send_complete(self, summary: dict):
        await self.broadcast({"type": "complete", "data": summary})

    async def send_error(self, error: str, step_id: str = ""):
        await self.broadcast({
            "type": "error",
            "data": {"error": error, "step_id": step_id}
        })


manager = WebSocketManager()
