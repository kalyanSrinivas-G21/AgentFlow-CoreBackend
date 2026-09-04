# backend/tests/e2e/test_slice2_task_to_llm.py
import pytest
import asyncio
import httpx
import os

API_BASE = "http://localhost:8000/api/v1"
# Fallback to the project ID created by the user in Stage 4
PROJECT_ID = os.getenv("TEST_PROJECT_ID", "921a4835-2c5f-43de-966d-be1e6bfd2434")

@pytest.mark.asyncio
async def test_end_to_end_worker_llm_execution():
    """
    Validates the full Slice 2 async loop: 
    API -> DB -> Redis Bus -> Worker -> Ollama LLM -> DB.
    Requires FastAPI (port 8000) and the Worker container to be running.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Create the task via API
        payload = {
            "task_type": "general",
            "input_payload": {"prompt": "Reply with exactly one word: 'Success'."}
        }
        create_resp = await client.post(f"{API_BASE}/projects/{PROJECT_ID}/tasks", json=payload)
        assert create_resp.status_code == 201, f"Failed to create task: {create_resp.text}"
        
        task_data = create_resp.json()
        task_id = task_data["id"]
        assert task_data["status"] == "QUEUED"

        # 2. Poll for completion
        max_attempts = 60
        poll_interval = 2.0
        final_status = None
        result_payload = None

        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)
            
            get_resp = await client.get(f"{API_BASE}/tasks/{task_id}")
            assert get_resp.status_code == 200
            
            current_task = get_resp.json()
            final_status = current_task["status"]
            
            if final_status in ("COMPLETED", "FAILED"):
                result_payload = current_task.get("result_payload")
                break

        # 3. Assertions
        assert final_status == "COMPLETED", f"Task did not complete in time. Status: {final_status}"
        assert result_payload is not None, "Result payload is missing"
        assert "response" in result_payload, "LLM response missing from payload"
        assert "Success" in result_payload["response"], f"LLM returned unexpected output: {result_payload['response']}"