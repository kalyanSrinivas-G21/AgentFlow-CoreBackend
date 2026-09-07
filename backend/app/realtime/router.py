# backend/app/realtime/router.py
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from uuid import UUID
from app.realtime.manager import ws_manager
from app.security.auth import verify_ws_project_access
from app.db import async_session_maker

router = APIRouter(tags=["realtime"])

@router.websocket("/ws/projects/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    project_id: UUID, 
    token: str = Query(..., description="JWT token for WS connection")
):
    """
    Step 11.4: Secure WebSockets
    Establishes a real-time event feed for a specific project with strict RBAC validation.
    """
    async with async_session_maker() as db:
        try:
            await verify_ws_project_access(token, project_id, db)
        except Exception as e:
            await websocket.close(code=1008, reason=str(e))
            return
            
    await ws_manager.connect(websocket, project_id)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, project_id)