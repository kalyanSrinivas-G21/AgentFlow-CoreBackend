# backend/tests/conftest.py
import asyncio
import logging
import os
import pytest
import pytest_asyncio
import jwt
from uuid import uuid4
import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test database isolation — must be set before any app imports
# ---------------------------------------------------------------------------
# Tests must never inherit the development database implicitly.
original_database_url = os.getenv("DATABASE_URL")
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://admin:password@localhost:5433/sovereign_ai_test",
)
if (
    original_database_url
    and os.getenv("TEST_DATABASE_URL") == original_database_url
    and "sovereign_ai_test" not in original_database_url
):
    raise RuntimeError("TEST_DATABASE_URL must be different from DATABASE_URL")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")

# Suppress the FastAPI app's background tasks (realtime consumer, resource sampler)
# so they don't interfere with the isolated test worker lifecycle below.
os.environ.setdefault("DISABLE_BACKGROUND_TASKS", "1")

# ---------------------------------------------------------------------------
# App imports (after env vars are set)
# ---------------------------------------------------------------------------
from app.db import async_session_maker, engine, Base  # noqa: E402

import app.security.models    # noqa: E402 — register ORM models with metadata
import app.tasks.models       # noqa: E402
import app.agents.models      # noqa: E402
import app.tools.models       # noqa: E402
import app.events.models      # noqa: E402
import app.workspace.models   # noqa: E402
import app.monitoring.models  # noqa: E402


# ---------------------------------------------------------------------------
# Database lifecycle
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def prepare_integration_db():
    """Create all tables before each test; dispose engine after."""
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()


# ---------------------------------------------------------------------------
# Auth context
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_context():
    """
    Creates a real user, project, and project_member in the PostgreSQL test database.
    Signs a legitimate JWT token for API requests.

    JWT secret matches the fallback in app/security/auth.py so tokens validate
    without needing the JWT_SECRET env var in tests.
    """
    user_id = uuid4()
    project_id = uuid4()

    async with async_session_maker() as db:
        project = app.tasks.models.Project(
            id=project_id,
            name="Integration Test Project",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc),
        )
        user = app.security.models.User(
            id=user_id,
            username=f"test_{user_id.hex[:8]}",
            hashed_password="fake",
        )
        member = app.security.models.ProjectMember(
            project_id=project_id, user_id=user_id, role="admin"
        )
        db.add(project)
        db.add(user)
        db.add(member)
        await db.commit()

    # Must match the fallback in app/security/auth.py exactly
    secret = os.getenv("JWT_SECRET", "local-dev-only-secret-key-not-for-production-use!")
    token = jwt.encode(
        {"sub": str(user_id), "username": user.username}, secret, algorithm="HS256"
    )

    return {"project_id": str(project_id), "token": token, "user_id": str(user_id)}


# ---------------------------------------------------------------------------
# In-process worker fixture
# ---------------------------------------------------------------------------
#
# Starts the real worker consumption path inside the pytest asyncio event loop:
#
#   Redis Stream → StreamConsumer → process_event → TaskRunner
#     → AgentOrchestrator → WorkflowGraph → OllamaRuntime / Executor
#
# Pointed at the same test database (localhost:5433/sovereign_ai_test) and
# test Redis (localhost:6379) that the rest of the test suite uses.
#
# Scope: function — each requesting test gets a clean, isolated worker with a
# unique consumer-group name so runs don't interfere with each other.
#
# NOT autouse — only tests that create tasks and expect async processing request
# this fixture explicitly.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_worker():
    """
    Runs a real in-process worker against the test database + Redis.

    Yields a dict:
        {
            "worker_id": str,   # worker id used for lease attribution
        }

    The fixture starts two background coroutines:
        1. run_outbox_dispatcher  — forwards outbox rows to Redis Streams
        2. _worker_loop           — reads from stream:task, calls process_event

    Both are cancelled and cleaned up automatically after the test finishes.
    """
    from redis.asyncio import Redis as AsyncRedis
    from app.events.envelope import EventEnvelope
    from app.events.dispatcher import run_outbox_dispatcher
    from worker.main import process_event

    redis_url = os.environ["REDIS_URL"]
    worker_id = f"test_worker_{uuid4().hex[:8]}"

    # Use a unique consumer group per test to prevent cross-test message delivery
    group_name = f"test_grp_{uuid4().hex[:8]}"
    stream_name = "stream:task"

    redis_client = AsyncRedis.from_url(redis_url, decode_responses=True)

    # Create the consumer group (mkstream=True ensures the stream exists)
    from redis.exceptions import ResponseError as RedisResponseError
    try:
        await redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
    except RedisResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise

    stop_event = asyncio.Event()

    async def _worker_loop() -> None:
        """Drain stream:task until stop_event is set."""
        while not stop_event.is_set():
            try:
                results = await redis_client.xreadgroup(
                    group_name,
                    worker_id,
                    {stream_name: ">"},
                    count=10,
                    block=200,   # 200 ms — react quickly without busy-spinning
                )
                for raw_stream, messages in results:
                    sname = (
                        raw_stream.decode("utf-8")
                        if isinstance(raw_stream, bytes)
                        else raw_stream
                    )
                    for message_id, payload_raw in messages:
                        mid = (
                            message_id.decode("utf-8")
                            if isinstance(message_id, bytes)
                            else message_id
                        )
                        payload = {
                            (k.decode("utf-8") if isinstance(k, bytes) else k): (
                                v.decode("utf-8") if isinstance(v, bytes) else v
                            )
                            for k, v in payload_raw.items()
                        }
                        envelope_json = payload.get("envelope")
                        if not envelope_json:
                            await redis_client.xack(sname, group_name, mid)
                            continue

                        try:
                            envelope = EventEnvelope.model_validate_json(envelope_json)
                        except Exception as exc:
                            logger.error(
                                "test_worker: malformed envelope msg=%s err=%s", mid, exc
                            )
                            await redis_client.xack(sname, group_name, mid)
                            continue

                        # Per-message idempotency guard (TTL 1 hour)
                        idem_key = f"twrk_seen:{envelope.idempotency_key}"
                        is_new = await redis_client.setnx(idem_key, "1")
                        if is_new:
                            await redis_client.expire(idem_key, 3600)
                            try:
                                await process_event(envelope, redis_client, worker_id)
                            except Exception as exc:
                                logger.error(
                                    "test_worker: process_event error msg=%s err=%s",
                                    mid,
                                    exc,
                                    exc_info=True,
                                )

                        await redis_client.xack(sname, group_name, mid)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not stop_event.is_set():
                    logger.error("test_worker loop error: %s", exc)
                await asyncio.sleep(0.05)

    dispatcher_task = asyncio.create_task(run_outbox_dispatcher(redis_client))
    worker_task = asyncio.create_task(_worker_loop())

    try:
        yield {"worker_id": worker_id}
    finally:
        stop_event.set()
        worker_task.cancel()
        dispatcher_task.cancel()
        await asyncio.gather(worker_task, dispatcher_task, return_exceptions=True)
        # Clean up per-test idempotency keys
        async for key in redis_client.scan_iter("twrk_seen:*"):
            await redis_client.delete(key)
        await redis_client.aclose()


# ---------------------------------------------------------------------------
# Task completion polling helper
# ---------------------------------------------------------------------------

async def wait_for_task_completion(
    task_id: str,
    client,
    headers: dict,
    *,
    timeout: float = 60.0,
    poll_interval: float = 0.5,
) -> dict:
    """
    Polls /api/v1/tasks/{task_id} until the task reaches COMPLETED or FAILED,
    or the bounded timeout expires.

    Raises AssertionError on timeout rather than silently returning stale data.
    Returns the final task JSON dict.
    """
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    last_status = "UNKNOWN"
    while loop.time() < deadline:
        await asyncio.sleep(poll_interval)
        resp = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        assert resp.status_code == 200, (
            f"Task poll returned HTTP {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        last_status = data.get("status", "UNKNOWN")
        if last_status in ("COMPLETED", "FAILED"):
            return data
    raise AssertionError(
        f"Task {task_id} did not reach a terminal state within {timeout}s. "
        f"Last observed status: {last_status}."
    )
