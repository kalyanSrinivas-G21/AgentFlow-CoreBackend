# backend/tests/integration/test_event_bus.py
import asyncio
import json
import pytest
import pytest_asyncio
from uuid import uuid4
from redis.asyncio import Redis
from unittest.mock import AsyncMock, MagicMock

from app.events.catalog import TASK_CREATED
from app.events.envelope import EventEnvelope
from app.events.publisher import publish
from app.events.consumer import StreamConsumer

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def redis_client():
    client = Redis(host='localhost', port=6379, db=0, decode_responses=True)
    await client.flushdb()
    yield client
    await client.aclose()

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # Fixed: session.add is synchronous in SQLAlchemy, so we use MagicMock
    session.add = MagicMock()
    return session

async def test_publish_guarantees_db_before_redis(redis_client, mock_db_session):
    envelope = EventEnvelope(
        event_type=TASK_CREATED,
        source="test_runner",
        correlation_id=uuid4(),
        payload={"data": "test"}
    )
    
    await publish(mock_db_session, redis_client, envelope)
    
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    
    stream_name = envelope.stream_name
    assert stream_name == "stream:task"
    
    messages = await redis_client.xrange(stream_name, "-", "+")
    assert len(messages) == 1
    
    msg_id, msg_data = messages[0]
    stored_envelope = EventEnvelope.model_validate_json(msg_data["envelope"])
    assert stored_envelope.event_id == envelope.event_id

async def test_consumer_idempotency_and_xack(redis_client, mock_db_session):
    envelope = EventEnvelope(
        event_type=TASK_CREATED,
        source="test_runner",
        correlation_id=uuid4()
    )
    
    await publish(mock_db_session, redis_client, envelope)
    
    handler = AsyncMock()
    consumer = StreamConsumer(redis_client, "test_group", "test_worker", [envelope.stream_name])
    await consumer.initialize()
    
    consumer._running = True
    results = await redis_client.xreadgroup(
        consumer.group_name, consumer.consumer_name, consumer.streams, count=1, block=1
    )
    stream_name, messages = results[0]
    msg_id, payload = messages[0]
    
    env_parsed = EventEnvelope.model_validate_json(payload["envelope"])
    
    allowed = await consumer._check_idempotency(env_parsed.idempotency_key)
    assert allowed is True
    await handler(env_parsed)
    await redis_client.xack(stream_name, consumer.group_name, msg_id)
    handler.assert_awaited_once()
    
    allowed_duplicate = await consumer._check_idempotency(env_parsed.idempotency_key)
    assert allowed_duplicate is False
    
    pending = await redis_client.xpending(stream_name, consumer.group_name)
    assert pending["pending"] == 0

async def test_consumer_dlq_routing_on_failures(redis_client):
    envelope = EventEnvelope(event_type=TASK_CREATED, source="dlq_test", correlation_id=uuid4())
    stream_name = envelope.stream_name
    await redis_client.xadd(stream_name, {"envelope": envelope.model_dump_json()})
    
    consumer = StreamConsumer(redis_client, "dlq_group", "worker1", [stream_name])
    await consumer.initialize()
    
    results = await redis_client.xreadgroup(
        consumer.group_name, consumer.consumer_name, consumer.streams, count=1, block=1
    )
    msg_id = results[0][1][0][0]
    payload = results[0][1][0][1]
    
    for i in range(1, 5):
        attempts = await redis_client.hincrby(f"attempts:{msg_id}", "count", 1)
        if attempts >= consumer.max_attempts:
            await consumer._handle_dlq(stream_name, msg_id, payload)
            
    dlq_messages = await redis_client.xrange(f"stream:task.deadletter", "-", "+")
    assert len(dlq_messages) == 1
    
    pending = await redis_client.xpending(stream_name, consumer.group_name)
    assert pending["pending"] == 0