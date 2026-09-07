# backend/app/events/dispatcher.py
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.events.models import OutboxEvent
from app.db import async_session_maker

logger = logging.getLogger(__name__)

async def run_outbox_dispatcher(redis_client: Redis):
    """
    Background loop that durably forwards PostgreSQL outbox events to Redis Streams.
    Uses SKIP LOCKED to allow multiple dispatchers to run concurrently without collisions.
    """
    logger.info("Starting Transactional Outbox Dispatcher...")
    while True:
        try:
            async with async_session_maker() as session:
                stmt = (
                    select(OutboxEvent)
                    .where(OutboxEvent.processed == False)
                    .order_by(OutboxEvent.created_at)
                    .limit(50)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(stmt)
                events = result.scalars().all()

                for event in events:
                    try:
                        await redis_client.xadd(
                            event.stream_name,
                            {
                                "envelope": event.event_payload,
                                "idempotency_key": event.idempotency_key
                            }
                        )
                        event.processed = True
                    except Exception as e:
                        logger.error(f"Redis XADD failed for outbox event {event.id}: {e}")
                
                if events:
                    await session.commit()
        except asyncio.CancelledError:
            logger.info("Outbox Dispatcher gracefully cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in outbox dispatcher loop: {e}")
        
        await asyncio.sleep(1.0)