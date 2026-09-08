import os

os.environ["DISABLE_BACKGROUND_TASKS"] = "1"

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import get_current_user
from app.security.application_auditor import ApplicationTelemetryAuditor
from app.security.sovereignty import TrustedNetworkPolicy


@pytest.fixture
def auditor():
    return ApplicationTelemetryAuditor(
        policy=TrustedNetworkPolicy(
            trusted_hosts=["db.internal"],
            trusted_subnets=["10.20.0.0/16"],
            local_ai_services=["ollama"],
            knowledge_services=["qdrant"],
            sandbox_services=["sandbox"],
            cloud_ai_services=["api.openai.com"],
            external_api_hosts=["example.invalid"],
            default_external_decision="blocked",
        )
    )


@pytest.mark.asyncio
async def test_fresh_metrics_distinguish_measured_local_zero_from_unobserved_external(auditor):
    metrics = await auditor.metrics()

    assert metrics.local_request_count == 0
    assert metrics.category_status["local_request_count"] == "measured"
    assert metrics.external_api_request_count is None
    assert metrics.category_status["external_api_request_count"] == "not_observed"
    assert metrics.cloud_ai_request_count is None
    assert metrics.category_status["cloud_ai_request_count"] == "not_observed"
    assert metrics.monitoring_capability == "Application Level Monitoring Active"


@pytest.mark.asyncio
async def test_classifies_and_counts_real_application_external_attempt(auditor):
    queue = await auditor.subscribe()

    async def observe_request(request: httpx.Request):
        await auditor.record_request(
            str(request.url),
            source_component="controlled_external_test",
            request_classification="controlled_test_attempt",
        )

    async with httpx.AsyncClient(
        event_hooks={"request": [observe_request]},
        timeout=0.1,
    ) as client:
        with pytest.raises(httpx.RequestError):
            await client.get("http://example.invalid/controlled-test")

    metrics = await auditor.metrics()
    assert metrics.external_api_request_count == 1
    assert metrics.category_status["external_api_request_count"] == "measured"
    assert metrics.blocked_external_request_count == 1
    assert metrics.recent_events[-1].decision == "blocked"
    assert metrics.recent_events[-1].destination_category == "external_api"
    envelope = await queue.get()
    assert envelope.status == "failed"
    assert envelope.payload["decision"] == "blocked"
    assert "technical_failure_count" not in metrics.model_dump()
    await auditor.unsubscribe(queue)


@pytest.mark.asyncio
async def test_disabled_adapter_reports_unavailable_without_stale_active_state(auditor):
    await auditor.set_enabled(False)

    metrics = await auditor.metrics()

    assert auditor.capability() == "Unavailable"
    assert metrics.monitoring_capability == "Unavailable"
    with pytest.raises(RuntimeError, match="unavailable"):
        await auditor.record_request("http://ollama:11434", source_component="test")


@pytest.mark.asyncio
async def test_local_ai_event_emits_phase15_envelope(auditor):
    queue = await auditor.subscribe()
    await auditor.record_request(
        "http://ollama:11434",
        source_component="ollama_provider",
        request_classification="local_ai_inference",
        bytes_transferred=12,
    )

    envelope = await queue.get()
    assert envelope.event_type == "sovereignty.network.observed"
    assert envelope.stream_name == "stream:sovereignty"
    assert envelope.sequence_number == 1
    assert envelope.payload["destination_category"] == "local_ai_inference"
    assert envelope.payload["decision"] == "allowed"

    await auditor.unsubscribe(queue)


def test_metrics_api_exposes_observation_states():
    app.dependency_overrides[get_current_user] = lambda: {"id": "contract-test"}
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/sovereignty/metrics")
        assert response.status_code == 200
        payload = response.json()
        assert payload["local_request_count"] == 0
        assert payload["external_api_request_count"] is None
        assert payload["category_status"]["external_api_request_count"] == "not_observed"
        assert payload["monitoring_capability"] == "Application Level Monitoring Active"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
