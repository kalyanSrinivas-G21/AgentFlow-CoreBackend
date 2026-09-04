# backend/app/events/publisher.py
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.events.envelope import EventEnvelope
from app.events.models import EventRecord

async def publish(db_session: AsyncSession, redis_client: Redis, envelope: EventEnvelope) -> None:
    """
    Durably publishes an event using a two-phase commit:
    1. Persist to PostgreSQL (authoritative log)
    2. Inject into the appropriate Redis stream
    """
    # 1. Persist to Postgres
    db_event = EventRecord(
        id=envelope.event_id,
        event_type=envelope.event_type,
        occurred_at=envelope.occurred_at.replace(tzinfo=None),
        source=envelope.source,
        task_id=envelope.task_id,
        agent_run_id=envelope.agent_run_id,
        correlation_id=envelope.correlation_id,
        causation_id=envelope.causation_id,
        payload=envelope.payload,
        schema_version=envelope.schema_version
    )
    
    db_session.add(db_event)
    await db_session.flush()
    await db_session.commit()

    # 2. Publish to Redis Stream
    stream_name = envelope.stream_name
    event_data = {
        "envelope": envelope.model_dump_json()
    }
    
    await redis_client.xadd(stream_name, event_data)