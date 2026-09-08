import inspect
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.agents.contracts import ExecutionTraceEvent, ExecutionTraceSink
from app.artifacts.contracts import ArtifactRecord, ArtifactStore
from app.events.contracts import EventEnvelope
from app.models_ai.contracts import ModelCatalog, ModelRuntime
from app.monitoring.contracts import ResourceTelemetry, TelemetryObservation, TelemetryProvider
from app.security.sovereignty import SovereigntyAuditor
from app.tools.contracts import ToolDefinition, ToolExecutor, ToolRegistry


def assert_abstract_contract(contract, method_names):
    for method_name in method_names:
        method = getattr(contract, method_name)
        assert callable(method)
        assert getattr(method, "__isabstractmethod__", False)


@pytest.mark.parametrize(
    ("contract", "methods"),
    [
        (TelemetryProvider, ["collect", "capability"]),
        (ResourceTelemetry, ["collect_resource_snapshot"]),
        (SovereigntyAuditor, ["observe", "classify", "capability", "metrics"]),
        (ModelCatalog, ["get", "list", "register", "update_status"]),
        (ModelRuntime, ["load_model", "unload_model", "check_model_status", "run_inference", "stream_inference", "get_resource_usage", "health_check"]),
        (ToolRegistry, ["register", "get", "list", "validate_input"]),
        (ToolExecutor, ["execute"]),
        (ArtifactStore, ["create", "get", "list_for_task"]),
        (ExecutionTraceSink, ["append", "list_for_execution"]),
    ],
)
def test_contract_methods_are_abstract(contract, methods):
    assert_abstract_contract(contract, methods)
    for method_name in methods:
        assert "NotImplementedError" in inspect.getsource(getattr(contract, method_name))


def test_event_envelope_has_ordering_and_execution_context():
    event = EventEnvelope(event_type="agent.started", component="orchestrator", status="in_progress", sequence_number=1)
    assert event.execution_id is None
    assert event.sequence_number == 1
    assert event.timestamp.tzinfo is not None


def test_execution_trace_rejects_hidden_reasoning_field():
    event = ExecutionTraceEvent(
        task_id=uuid4(),
        execution_id=uuid4(),
        step_id=uuid4(),
        step_type="planning",
        component="orchestrator",
        start_time=datetime.now(timezone.utc),
        status="succeeded",
        safe_summary="Plan created",
    )
    assert "reasoning" not in ExecutionTraceEvent.model_fields
    assert event.safe_summary == "Plan created"


def test_contract_models_validate_required_metadata():
    observation = TelemetryObservation(
        metric_name="gpu.vram.used",
        unit="MB",
        observed_at=datetime.now(timezone.utc),
        source="nvml",
        state="unavailable",
    )
    assert observation.value is None

    tool = ToolDefinition(
        tool_id="sandbox.execute",
        name="Sandbox execution",
        description="Run approved code in an isolated sandbox",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        permission_level="execute",
        execution_environment="sandbox",
        timeout_seconds=30,
        health="available",
    )
    assert tool.requires_approval is False


def test_artifact_contract_keeps_task_and_step_provenance():
    record = ArtifactRecord(
        artifact_id=uuid4(),
        artifact_type="report",
        file_name="report.md",
        workspace_location="artifacts/report.md",
        task_id=uuid4(),
        execution_id=uuid4(),
        generating_step_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    assert record.task_id is not None
    assert record.generating_step_id is not None
