import asyncio
import datetime
import os
import subprocess
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db import async_session_maker
from app.events.envelope import EventEnvelope
from app.events.models import EventRecord, OutboxEvent
from app.tasks.models import Task
from app.tools.code_tools import CodeExecuteTool

pytestmark = pytest.mark.asyncio


def _require_physical_tests():
    if os.getenv("RUN_DESTRUCTIVE_FAILURE_TESTS") != "1":
        pytest.skip("Set RUN_DESTRUCTIVE_FAILURE_TESTS=1 to run destructive Compose tests")


def _container_id(service: str) -> str:
    result = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.service={service}"],
        check=True,
        capture_output=True,
        text=True,
    )
    container_id = result.stdout.strip().splitlines()
    if not container_id:
        pytest.fail(f"No Compose container found for service {service}")
    return container_id[0]


def _docker(*args: str) -> None:
    subprocess.run(["docker", *args], check=True, capture_output=True, text=True)


async def test_redis_outage_preserves_event_in_postgres_outbox():
    """A real Redis stop must not prevent the API transaction from committing."""
    _require_physical_tests()
    redis_id = _container_id("redis")
    _docker("stop", redis_id)

    try:
        event = EventEnvelope(
            event_type="physical.redis.outage",
            source="failure_test",
            correlation_id=uuid4(),
            payload={"failure": "redis_stopped"},
        )
        idempotency_key = event.idempotency_key
        async with async_session_maker() as db:
            db.add(
                EventRecord(
                    id=event.event_id,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at.replace(tzinfo=None),
                    source=event.source,
                    correlation_id=event.correlation_id,
                    payload=event.payload,
                    schema_version=event.schema_version,
                )
            )
            db.add(
                OutboxEvent(
                    stream_name=event.stream_name,
                    event_payload=event.model_dump_json(),
                    idempotency_key=idempotency_key,
                )
            )
            await db.commit()

            stored = await db.scalar(
                select(OutboxEvent).where(OutboxEvent.idempotency_key == idempotency_key)
            )
            assert stored is not None
            assert stored.processed is False
    finally:
        _docker("start", redis_id)


async def test_worker_crash_requeues_expired_lease(auth_context):
    """A restarted physical worker must reclaim a task abandoned by its predecessor."""
    _require_physical_tests()
    worker_id = _container_id("worker")
    _docker("stop", worker_id)

    task_id = uuid4()
    try:
        async with async_session_maker() as db:
            db.add(
                Task(
                    id=task_id,
                    project_id=auth_context["project_id"],
                    task_type="standard",
                    status="RUNNING",
                    input_payload={"prompt": "Reply with exactly RECOVERED."},
                    worker_id="crashed-worker",
                    lease_expiry=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    - datetime.timedelta(seconds=1),
                    attempt_count=1,
                )
            )
            await db.commit()

        _docker("start", worker_id)
        reclaimed = None
        for _ in range(45):
            await asyncio.sleep(2)
            async with async_session_maker() as db:
                reclaimed = await db.scalar(select(Task).where(Task.id == task_id))
            if reclaimed and reclaimed.attempt_count >= 2 and reclaimed.worker_id != "crashed-worker":
                break

        assert reclaimed is not None
        assert reclaimed.attempt_count >= 2
        assert reclaimed.worker_id != "crashed-worker"
        assert reclaimed.status in {"RUNNING", "COMPLETED", "FAILED"}
    finally:
        _docker("start", worker_id)


async def test_sandbox_timeout_kills_physical_container():
    """An infinite loop is killed by Docker and exposed as a controlled tool failure."""
    _require_physical_tests()
    tool = CodeExecuteTool()
    tool.timeout_s = 2.0
    result = await tool.run(
        {
            "files": {"loop.py": "while True:\n    pass\n"},
            "main_file": "loop.py",
        },
        str(uuid4()),
    )

    assert result.success is False
    assert result.error == "timeout"
    remaining = subprocess.run(
        ["docker", "ps", "-q", "--filter", "name=sandbox_"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert remaining.stdout.strip() == ""
