# backend/tests/e2e/test_slice2_task_to_llm.py
"""
Slice 2 E2E: Full async loop — API → DB → Redis → Worker → LLM → DB.

Original test hit localhost:8000 directly and required a separately running
server + worker, making it impossible to run under standard pytest.

Repaired to use ASGI transport (same pattern as test_real_agent_workflow.py)
with the in-process test_worker fixture so the full loop runs in pytest.

If Ollama is unreachable or has no loaded model the test is SKIPPED.
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio


async def _ollama_is_available() -> bool:
    """Return True if Ollama is reachable and has a routable model loaded."""
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
            router = ModelRouter()
            try:
                model_id = router.route(required_capabilities=["general"])
                return model_id in loaded_names
            except ValueError:
                return False
    except Exception:
        return False


async def test_end_to_end_worker_llm_execution(auth_context, test_worker):
    """
    Validates the full Slice 2 async loop:
        API → DB → Redis Stream → Worker → Ollama LLM → DB

    Previously required a live server on localhost:8000 + running worker
    container.  Repaired to use ASGI transport + in-process test_worker.
    """
    from tests.conftest import wait_for_task_completion

    if not await _ollama_is_available():
        pytest.skip(
            "BLOCKED — LOCAL MODEL RUNTIME UNAVAILABLE: "
            "Ollama unreachable or no routable model loaded. "
            "Environment constraint, not a code defect."
        )

    project_id = auth_context["project_id"]
    headers = {"Authorization": f"Bearer {auth_context['token']}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Create the task via API
        payload = {
            "task_type": "general",
            "input_payload": {"prompt": "Reply with exactly one word: 'Success'."},
        }
        create_resp = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json=payload,
            headers=headers,
        )
        assert create_resp.status_code == 201, (
            f"Failed to create task: {create_resp.text}"
        )
        task_data = create_resp.json()
        task_id = task_data["id"]
        assert task_data["status"] == "QUEUED"

        # 2. Wait for in-process worker to process it (bounded poll)
        data = await wait_for_task_completion(
            task_id, client, headers, timeout=60.0, poll_interval=0.5
        )

        # 3. Assertions
        assert data["status"] == "COMPLETED", (
            f"Task did not complete. status={data['status']}, "
            f"result={data.get('result_payload')}"
        )
        result_payload = data.get("result_payload") or {}
        assert "response" in result_payload, (
            f"LLM response missing from payload: {result_payload}"
        )
