# backend/app/realtime/router.py
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from uuid import UUID
from app.realtime.manager import ws_manager

router = APIRouter(tags=["realtime"])

# Defaulting to a safe fallback if not injected via env
DEMO_ADMIN_TOKEN = os.getenv("DEMO_ADMIN_TOKEN", "supersecret-demo-token")

@router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    project_id: UUID, 
    token: str = Query(..., description="Authentication token for WS connection")
):
    """
    Establishes a real-time event feed for a specific project.
    Validates the bearer token via query parameter.
    """
    if token != DEMO_ADMIN_TOKEN:
        await websocket.close(code=1008, reason="Unauthorized")
        return
        
    await ws_manager.connect(websocket, project_id)
    try:
        while True:
            # We don't expect the client to send us data, but we must listen 
            # to detect when the client closes the connection or sends keep-alives.
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, project_id)