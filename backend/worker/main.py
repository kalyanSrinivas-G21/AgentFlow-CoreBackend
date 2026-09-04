# backend/worker/main.py
import asyncio
import logging
import os
from redis.asyncio import Redis

# Assumes backend.app is available in PYTHONPATH
from app.db import async_session_maker
from app.events.consumer import StreamConsumer
from app.events.envelope import EventEnvelope
from app.tasks.runner import TaskRunner

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def process_event(envelope: EventEnvelope, redis_client: Redis):
    # Only process queued events
    if envelope.event_type not in ("task.queued", "TASK_QUEUED"):
        return

    task_id = envelope.task_id
    if not task_id:
        logger.error("Received task.queued event without a task_id")
        return

    logger.info(f"Worker acknowledged task {task_id}")
    async with async_session_maker() as session:
        runner = TaskRunner(session, redis_client)
        await runner.run(task_id)

async def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    redis_client = Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
    
    async def handler(envelope: EventEnvelope):
        await process_event(envelope, redis_client)

    consumer = StreamConsumer(
        redis_client=redis_client,
        group_name="worker_group",
        consumer_name=f"worker_{os.getpid()}",
        stream_names=["stream:task"]
    )
    
    logger.info("Initializing worker stream consumer...")
    await consumer.initialize()
    
    logger.info("Worker actively listening for 'task.queued' events...")
    await consumer.consume(handler)

if __name__ == "__main__":
    asyncio.run(main())