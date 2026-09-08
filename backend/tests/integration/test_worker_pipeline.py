# backend/tests/integration/test_worker_pipeline.py
"""
Worker pipeline integration test.

Intent: Prove the full asynchronous task processing loop:
    API → PostgreSQL outbox → Redis stream → Worker → LLM → DB

The test previously required a separately running worker container which
targeted a different database (db:5432) than the test database (localhost:5433),
causing tasks to remain QUEUED forever.

Fix: Uses the test_worker fixture (conftest.py) which runs the real
process_event → TaskRunner → OllamaRuntime path in-process, pointed at the
test database and test Redis.

If Ollama is unreachable the test is SKIPPED with a clear BLOCKED classification.
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio


async def _ollama_is_available() -> bool:
    """
    Return True if Ollama is reachable AND has at least one model that the
    ModelRouter would select for general capability loaded.
    """
    import httpx
    from app.models_ai.router_v2 import ModelRouter
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base}/api/tags")
            if r.status_code != 200:
                return False
            loaded_names = {m["name"] for m in r.json().get("models", [])}
            if not loaded_names:
                return False
            # Check that the router can select a model that is actually loaded
            router = ModelRouter()
            try:
                model_id = router.route(required_capabilities=["general"])
                return model_id in loaded_names
            except ValueError:
                return False
    except Exception:
        return False


async def test_worker_direct_llm_execution(auth_context, test_worker):
    """
    Step 12.3: Worker Integration Test.
    Proves the API → Outbox → Redis Stream → Worker → LLM → DB loop works
    end-to-end without relying on an external worker process.

    Previously SKIPPED due to database configuration mismatch (worker used
    db:5432, test used localhost:5433).  Fixed via in-process test_worker fixture.
    """
    from tests.conftest import wait_for_task_completion

    if not await _ollama_is_available():
        pytest.skip(
            "BLOCKED — LOCAL MODEL RUNTIME UNAVAILABLE: "
            "Ollama unreachable or no models loaded. "
            "Environment constraint, not a code defect."
        )

    project_id = auth_context["project_id"]
    headers = {"Authorization": f"Bearer {auth_context['token']}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Create task via the API
        req_data = {
            "task_type": "general",
            "input_payload": {"prompt": "Reply with exactly one word: APPLE."},
        }
        res = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json=req_data,
            headers=headers,
        )
        assert res.status_code == 201, f"Task creation failed: {res.text}"
        task_id = res.json()["id"]
        assert res.json()["status"] == "QUEUED"

        # 2. Wait for the in-process worker to process it
        data = await wait_for_task_completion(
            task_id, client, headers, timeout=60.0, poll_interval=0.5
        )

        # 3. Verify outcome
        assert data["status"] == "COMPLETED", (
            f"Task did not complete. Status={data['status']}, "
            f"result={data.get('result_payload')}"
        )
        result = data.get("result_payload") or {}
        assert "response" in result, (
            f"LLM response missing from result_payload: {result}"
        )
        assert "APPLE" in str(result.get("response", "")).upper(), (
            f"LLM output missing expected word. Got: {result.get('response')!r}"
        )
