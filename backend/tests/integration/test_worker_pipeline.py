# backend/tests/integration/test_worker_pipeline.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio

async def test_worker_direct_llm_execution(auth_context):
    """
    Step 12.3: Worker Integration Test.
    Proves the API -> Outbox -> Redis Stream -> Worker -> LLM -> DB loop works perfectly without mocks.
    """
    project_id = auth_context["project_id"]
    headers = {"Authorization": f"Bearer {auth_context['token']}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Dispatch Task to the API
        req_data = {
            "task_type": "standard",
            "input_payload": {"prompt": "Reply with exactly the word APPLE and nothing else."}
        }
        res = await client.post(f"/api/v1/projects/{project_id}/tasks", json=req_data, headers=headers)
        assert res.status_code == 201, f"Failed to create task: {res.text}"
        task_id = res.json()["id"]
        
        # 2. Wait for the background worker container to process the stream
        for _ in range(30):
            await asyncio.sleep(2)
            poll = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
            assert poll.status_code == 200
            data = poll.json()
            
            if data["status"] in ["COMPLETED", "FAILED"]:
                assert data["status"] == "COMPLETED"
                # Validate the LLM output was saved correctly by the background worker
                assert "APPLE" in str(data.get("result_payload", "")).upper()
                return
        
        pytest.fail("Worker pipeline timed out. Background worker failed to process the task.")