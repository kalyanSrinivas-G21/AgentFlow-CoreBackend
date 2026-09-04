# backend/app/realtime/manager.py
import asyncio
import json
import logging
from typing import Dict, List
from uuid import UUID
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy import select

from app.tasks.models import Task

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps project_id to a list of active WebSocket connections
        self.active_connections: Dict[UUID, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: UUID):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        logger.info(f"WebSocket connected for project: {project_id}")

    def disconnect(self, websocket: WebSocket, project_id: UUID):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info(f"WebSocket disconnected for project: {project_id}")

    async def broadcast_to_project(self, project_id: UUID, message: str):
        connections = self.active_connections.get(project_id, [])
        dead_connections = []
        
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to websocket: {e}")
                dead_connections.append(connection)
                
        # Clean up connections that dropped ungracefully
        for dead in dead_connections:
            self.disconnect(dead, project_id)

ws_manager = ConnectionManager()

async def get_project_id_for_task(task_id: UUID) -> UUID | None:
    """Helper to map a task_id found in a Redis event back to its project_id for filtering."""
    try:
        from app.db import async_session_maker
        async with async_session_maker() as session:
            result = await session.execute(select(Task.project_id).where(Task.id == task_id))
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to query project_id for task {task_id}: {e}")
        return None

async def consume_redis_streams(redis_url: str):
    """Background task to tail Redis streams and push to WebSockets."""
    logger.info("Starting Redis Stream consumer for WebSockets")
    redis = Redis.from_url(redis_url, decode_responses=True)
    
    # We only care about new events from the moment the server starts ('$')
    streams = {
        "stream:task": "$",
        "stream:agent": "$",
        "stream:tool": "$",
        "stream:validation": "$",
        "stream:system": "$"
    }
    
    while True:
        try:
            # Block for up to 1000ms waiting for new events
            results = await redis.xread(streams, count=10, block=1000)
            
            for stream_name, messages in results:
                for message_id, data in messages:
                    # Update pointer so we don't read this message again
                    streams[stream_name] = message_id
                    
                    if "payload" in data:
                        event_payload = data["payload"]
                        try:
                            event_dict = json.loads(event_payload)
                            task_id_str = event_dict.get("task_id")
                            
                            if task_id_str:
                                task_id = UUID(task_id_str)
                                project_id = await get_project_id_for_task(task_id)
                                
                                if project_id:
                                    # Forward the raw JSON directly to the matching project room
                                    await ws_manager.broadcast_to_project(project_id, event_payload)
                                    
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON payload in stream {stream_name}: {event_payload}")
                        except Exception as e:
                            logger.error(f"Error processing stream message {message_id}: {e}")
                            
        except asyncio.CancelledError:
            logger.info("Redis consumer task cancelled. Shutting down cleanly.")
            break
        except Exception as e:
            logger.error(f"Redis consumer connection error: {e}")
            await asyncio.sleep(5)  # Backoff on connection drop