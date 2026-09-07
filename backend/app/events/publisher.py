# backend/app/events/publisher.py
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.events.envelope import EventEnvelope
from app.events.models import EventRecord, OutboxEvent

async def publish(db_session: AsyncSession, redis_client: Redis, envelope: EventEnvelope) -> None:
    """
    Transactional Outbox Publisher.
    Writes the event log and the outbox message to the active PostgreSQL transaction.
    Does NOT commit the transaction or directly contact Redis.
    """
    # 1. Persist to Postgres (Authoritative Audit Log)
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
    
    # 2. Persist to Transactional Outbox (Pending Redis Delivery)
    outbox_event = OutboxEvent(
        stream_name=envelope.stream_name,
        event_payload=envelope.model_dump_json(),
        idempotency_key=envelope.idempotency_key
    )
    db_session.add(outbox_event)
    
    # Flush to ensure schema violations are caught immediately within the caller's transaction
    await db_session.flush()