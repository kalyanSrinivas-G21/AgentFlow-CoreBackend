# backend/worker/main.py
import asyncio
import datetime
import logging
import os
from redis.asyncio import Redis
from sqlalchemy import select

from app.db import async_session_maker
from app.events.consumer import StreamConsumer
from app.events.envelope import EventEnvelope
from app.tasks.runner import TaskRunner
from app.events.dispatcher import run_outbox_dispatcher
from app.events.publisher import publish
from app.events import catalog
from app.tasks.models import Task

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Track asyncio Tasks for Active Cancellation
active_tasks = {}

async def _run_task_wrapper(redis_client: Redis, worker_id: str, task_id: str):
    """Wraps TaskRunner to safely handle lifecycle and cancellation cleanup."""
    async with async_session_maker() as session:
        runner = TaskRunner(session, redis_client, worker_id)
        try:
            await runner.run(task_id)
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} successfully cancelled mid-execution.")
            from sqlalchemy import update
            from app.tasks.models import Task
            from app.events.publisher import publish
            
            # Step 10.3: Release worker lease and mark CANCELLED to prevent hanging
            await session.execute(
                update(Task).where(Task.id == task_id).values(
                    status="CANCELLED", worker_id=None, lease_expiry=None
                )
            )
            await session.commit()
            
            # Publish standardized completion envelope
            cancel_evt = EventEnvelope(
                event_type="task.cancelled", source="worker", task_id=task_id,
                correlation_id=task_id, payload={"status": "CANCELLED"}
            )
            await publish(session, redis_client, cancel_evt)
            await session.commit()
            raise  # Re-raise to ensure proper internal cleanup
        finally:
            active_tasks.pop(task_id, None)

async def process_event(envelope: EventEnvelope, redis_client: Redis, worker_id: str):
    task_id = str(envelope.task_id) if envelope.task_id else None
    if not task_id:
        return

    if envelope.event_type in ("task.queued", "TASK_QUEUED"):
        logger.info(f"Worker {worker_id} acknowledging task {task_id}")
        task = asyncio.create_task(_run_task_wrapper(redis_client, worker_id, task_id))
        active_tasks[task_id] = task

    elif envelope.event_type in ("task.cancel.requested", "TASK_CANCEL_REQUESTED"):
        logger.info(f"Worker {worker_id} received cancel request for task {task_id}")
        if task_id in active_tasks:
            logger.info(f"Interrupting active task {task_id}...")
            active_tasks[task_id].cancel()

async def recover_expired_tasks(redis_client: Redis):
    """Return work abandoned by a worker crash to the durable task queue."""
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    async with async_session_maker() as session:
        result = await session.execute(
            select(Task).where(
                Task.status == "RUNNING",
                Task.lease_expiry.is_not(None),
                Task.lease_expiry < now,
            ).with_for_update(skip_locked=True)
        )
        expired_tasks = result.scalars().all()
        for task in expired_tasks:
            task.status = "QUEUED"
            task.worker_id = None
            task.lease_expiry = None
            task.heartbeat = None
            await publish(
                session,
                redis_client,
                EventEnvelope(
                    event_type=catalog.TASK_QUEUED,
                    source="worker_recovery",
                    task_id=task.id,
                    correlation_id=task.id,
                    payload={"status": "QUEUED", "reason": "worker_lease_expired"},
                ),
            )
        if expired_tasks:
            await session.commit()
        return len(expired_tasks)

async def lease_recovery_loop(redis_client: Redis):
    while True:
        try:
            await recover_expired_tasks(redis_client)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Expired task lease recovery failed")
        await asyncio.sleep(float(os.getenv("TASK_RECOVERY_INTERVAL_SECONDS", "5")))

async def main():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = Redis.from_url(redis_url, decode_responses=True)
    worker_id = f"worker_{os.getpid()}_{os.urandom(4).hex()}"
    
    dispatcher_task = asyncio.create_task(run_outbox_dispatcher(redis_client))
    recovery_task = asyncio.create_task(lease_recovery_loop(redis_client))
    
    async def handler(envelope: EventEnvelope):
        await process_event(envelope, redis_client, worker_id)

    consumer = StreamConsumer(
        redis_client=redis_client,
        group_name="worker_group",
        consumer_name=worker_id,
        stream_names=["stream:task"]
    )
    
    logger.info(f"Initializing worker stream consumer (ID: {worker_id})...")
    await consumer.initialize()
    logger.info("Worker actively listening for events...")
    
    try:
        await consumer.consume(handler)
    finally:
        dispatcher_task.cancel()
        recovery_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())