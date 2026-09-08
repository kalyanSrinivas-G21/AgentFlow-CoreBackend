import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.security.auth import get_current_user
from app.security.auditor import get_application_auditor

router = APIRouter(
    prefix="/api/v1/sovereignty",
    tags=["Sovereignty"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/metrics")
async def get_sovereignty_metrics():
    """Return application-observed sovereignty metrics with explicit state labels."""
    return (await get_application_auditor().metrics()).model_dump(mode="json")


@router.get("/events")
async def sovereignty_events():
    """Stream Phase 15 sovereignty envelopes as bounded Server-Sent Events."""
    auditor = get_application_auditor()
    queue = await auditor.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    envelope = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: {envelope.event_type}\ndata: {envelope.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    yield ": sovereignty-auditor-heartbeat\n\n"
        finally:
            await auditor.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
