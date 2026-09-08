# PS26117 Phase 15 Interface Contracts

**Stage:** Three — Interfaces and Contracts  
**Date:** 2026-09-07  
**Entry baseline:** `docs/phase15/GAP_ANALYSIS.md` was read in full and remains authoritative. No contradiction was found during this stage.

## Contract Rules

These contracts define boundaries only. The modules added in this stage contain typed models and abstract methods that raise `NotImplementedError`; they do not call Ollama, NVML, PostgreSQL, Redis, Docker, a network adapter, a tool, or a filesystem provider. Concrete implementations belong to later stages.

All absent measurements use an explicit observation state rather than a fabricated zero. All event and trace payloads are metadata-only and must not contain hidden model reasoning or confidential payloads.

## 1. Telemetry Interface

**Responsibility:** Represent sourced resource and runtime observations and expose the actual monitoring capability of a provider. A provider must distinguish measured zero from not observed, unavailable, unknown, blocked, and allowed.

**Definitions:** `backend/app/monitoring/contracts.py`

- `TelemetryObservation(metric_name: str, value: Optional[float], unit: str, observed_at: datetime, source: str, state: ObservationState, confidence: Optional[float], labels: dict[str, str])`
- `TelemetrySnapshot(observations: list[TelemetryObservation], capability: MonitoringCapability, collected_at: datetime)`
- `TelemetryProvider.collect() -> TelemetrySnapshot`
- `TelemetryProvider.capability() -> MonitoringCapability`
- `ResourceTelemetry.collect_resource_snapshot() -> TelemetrySnapshot`

**Reconciles:** Gap Analysis Sections 13-15, 18, and 19. It supplies the source/confidence/state vocabulary missing from `monitoring/sampler.py` and `models_ai/resource_manager.py`, where unavailable GPU values can currently resemble zero.

**Bypassing call sites to redirect later:**

- `backend/app/monitoring/sampler.py:53` writes a `ResourceMetric` snapshot directly; Stage Four must publish `TelemetryObservation` values and preserve unavailable state.
- `backend/app/models_ai/resource_manager.py:43` returns a raw NVML dictionary and `:46-48` returns zero-like values when unavailable; Stage Five must expose this through `ResourceTelemetry`.
- `backend/app/monitoring/router.py` currently serializes `ResourceMetric` directly; Stage Four/Stage Nine must consume the typed snapshot contract.

## 2. Network Auditor Interface

**Responsibility:** Observe metadata-only network activity, classify destinations using an explicit trusted-network policy, report capability honestly, and aggregate sovereignty metrics. Application-level request logging, container/process telemetry, and host adapters must implement the same boundary.

**Definitions:** `backend/app/security/sovereignty.py`

- `TrustedNetworkPolicy(trusted_hosts, trusted_subnets, local_ai_services, knowledge_services, sandbox_services, cloud_ai_services, external_api_hosts, default_external_decision)`
- `NetworkAuditEvent(timestamp, source_component, source_process, destination_category, destination_address, destination_service, protocol, direction, bytes_transferred, request_classification, decision, task_id, execution_id)`
- `SovereigntyMetrics(local_request_count, local_ai_request_count, internal_request_count, external_api_request_count, cloud_ai_request_count, blocked_external_request_count, external_bytes, local_bytes, monitoring_capability, security_policy_state, category_status, observation_scope, recent_events, last_external_connection, last_cloud_ai_request)`
- `SovereigntyAuditor.observe() -> list[NetworkAuditEvent]`
- `SovereigntyAuditor.classify(destination: str, policy: TrustedNetworkPolicy) -> DestinationCategory`
- `SovereigntyAuditor.capability() -> str`
- `SovereigntyAuditor.metrics() -> SovereigntyMetrics`

**Reconciles:** Gap Analysis Sections 1, 14, 18, 20, and 21. It creates the missing policy, event, capability, and `/api/v1/sovereignty/metrics` implementation target without claiming host-level visibility.

**Bypassing call sites to redirect later:**

- `backend/app/security/auth.py:20` (`validate_local_endpoint`) currently validates selected endpoint URLs only; Stage Four must route endpoint decisions and application requests through the auditor/policy boundary.
- `backend/app/models_ai/ollama_provider.py:21` and `:80` issue model HTTP operations through the provider; Stage Four/Five must emit an audit event for each request through the network auditor.
- `backend/app/sandbox/runner.py:31` owns `--network=none`; Stage Eight must report sandbox network policy/events through the same classification contract without claiming host telemetry.
- `backend/tests/integration/test_no_external_egress.py` uses an HTTPX monkeypatch, which remains a test mechanism, not production network observation.

## 3. Model Runtime Interface

**Responsibility:** Provide one provider-neutral boundary for local model lifecycle, status, inference, streaming, resource usage, and health. Provider adapters such as Ollama must be behind this interface so orchestration cannot call runtime-specific clients directly.

**Definitions:** `backend/app/models_ai/contracts.py`

- `ModelStatus(availability: bool, load_state: LoadState, health: ModelHealth, updated_at: datetime, failure_reason: Optional[str])`
- `ModelInferenceRequest(model_id: str, prompt: str, system: Optional[str], options: dict[str, Any], task_id: Optional[UUID], execution_id: Optional[UUID])`
- `ModelResourceUsage(model_id: str, used_vram_mb: Optional[int], available_vram_mb: Optional[int], source: str, observed_at: datetime)`
- `ModelRuntime.load_model(model: ModelCatalogEntry) -> ModelStatus`
- `ModelRuntime.unload_model(model_id: str) -> ModelStatus`
- `ModelRuntime.check_model_status(model_id: str) -> ModelStatus`
- `ModelRuntime.run_inference(request: ModelInferenceRequest) -> str`
- `ModelRuntime.stream_inference(request: ModelInferenceRequest) -> AsyncIterator[str]`
- `ModelRuntime.get_resource_usage(model_id: str) -> ModelResourceUsage`
- `ModelRuntime.health_check(model_id: str) -> ModelStatus`

**Reconciles:** Gap Analysis Sections 2, 3, 11, 13, 18, 19, and 24. It sets up provider-specific health, bounded loading, active-request-aware eviction, and no silent cloud fallback.

**Bypassing call sites to redirect later:**

- `backend/app/agents/graph.py:43` constructs `OllamaProvider` directly; `:58` and `:121` call `generate` directly.
- `backend/app/models_ai/router.py:32` constructs `OllamaProvider` directly; `:36` calls `stream` directly.
- `backend/app/workspace/embedding_service.py:13` constructs `OllamaProvider` directly; `:25` calls `embed` directly.
- `backend/app/models_ai/ollama_provider.py:12` owns `GPUResourceManager` directly; Stage Five must make resource admission and runtime lifecycle explicit through the runtime/resource boundary.

## 4. Model Catalog Interface

**Responsibility:** Persist model identity, capabilities, modalities, location, provider/runtime type, resource estimates, fallback support, devices, version, configuration, and current status. Routing must query this catalog rather than maintain model names in call sites.

**Definitions:** `backend/app/models_ai/contracts.py`

- `ModelCatalogEntry(model_id, display_name, provider_type, runtime_type, location, capabilities, modalities, context_limit, estimated_vram_mb, measured_vram_mb, cpu_fallback, gpu_required, supported_devices, version, configuration, status)`
- `ModelCatalog.get(model_id: str) -> Optional[ModelCatalogEntry]`
- `ModelCatalog.list(capability: Optional[str]) -> list[ModelCatalogEntry]`
- `ModelCatalog.register(model: ModelCatalogEntry) -> ModelCatalogEntry`
- `ModelCatalog.update_status(model_id: str, status: ModelStatus) -> ModelCatalogEntry`

**Reconciles:** Gap Analysis Sections 2, 13, 21, and 24. It replaces the current static registry as the future source of truth while retaining the existing API shape until migration.

**Bypassing call sites to redirect later:**

- `backend/app/models_ai/registry.py` contains the hardcoded `_REGISTRY` and `get_model/list_models` functions.
- `backend/app/models_ai/router.py:12-17` exposes the static registry; `:48-65` uses hardcoded priority chains and direct registry lookup.
- `backend/app/models_ai/resource_manager.py:10` and `:77` use static `get_model` metadata and admit unknown models blindly.
- `backend/app/agents/graph.py:47` selects the model from the current static router.

## 5. Tool Registry Interface

**Responsibility:** Make registered tools the sole agent-invokable capability boundary. The registry owns metadata and input validation; the executor later adds authorization, policy, environment allocation, timeout, cleanup, and telemetry.

**Definitions:** `backend/app/tools/contracts.py`

- `ToolDefinition(tool_id, name, description, input_schema, output_schema, permission_level, execution_environment, timeout_seconds, resource_limits, network_policy, supported_task_types, health, requires_approval)`
- `ToolRegistry.register(definition) -> ToolDefinition`
- `ToolRegistry.get(tool_id) -> Optional[ToolDefinition]`
- `ToolRegistry.list(task_type: Optional[str]) -> list[ToolDefinition]`
- `ToolRegistry.validate_input(tool_id, arguments) -> dict[str, Any]`
- `ToolExecutor.execute(tool_id, arguments, project_id, task_id) -> dict[str, Any]`

**Reconciles:** Gap Analysis Sections 3, 5, 9, 10, 16, 19, and 21. It gives the LangGraph path a contract to converge on the existing policy/schema executor rather than using a special sandbox-only branch.

**Bypassing call sites to redirect later:**

- `backend/app/agents/graph.py:11` calls `get_tool_catalog()` and `:89` calls `self.executor.execute_step()` through a local mock step.
- `backend/app/agents/orchestrator.py:13-26` accepts only the literal `sandbox` tool and calls `run_in_sandbox` directly.
- `backend/app/agents/executor.py:23-40` uses the legacy global `TOOL_REGISTRY`; Stage Six must adapt it to this contract rather than create a second registry.

## 6. Artifact Interface

**Responsibility:** Persist real deliverables with task, execution, and generating-step provenance, then expose stable preview/download/discovery metadata. Workspace paths remain subject to the existing canonical containment checks.

**Definitions:** `backend/app/artifacts/contracts.py`

- `ArtifactReference(artifact_id, artifact_type, file_name, workspace_location, preview_available, download_available)`
- `ArtifactRecord(..., task_id, execution_id, generating_step_id, created_at, size_bytes)`
- `ArtifactStore.create(task_id, execution_id, generating_step_id, artifact_type, file_name, content: bytes) -> ArtifactRecord`
- `ArtifactStore.get(artifact_id: UUID) -> ArtifactRecord`
- `ArtifactStore.list_for_task(task_id: UUID) -> list[ArtifactRecord]`

**Reconciles:** Gap Analysis Sections 6, 9, 17, 21, and 23. It sets up restoration of the removed artifact persistence and a traceable artifact-created event.

**Bypassing call sites to redirect later:**

- `backend/app/workspace/service.py:11-22` resolves workspace paths but has no artifact provenance boundary.
- `backend/app/agents/graph.py:89` receives tool output but has no artifact-generation step.
- `backend/app/agents/orchestrator.py:30-61` returns final payload without creating or returning artifact references.
- The initial artifacts table was removed by a later migration, so the future store must own a deliberate replacement migration.

## 7. Event Schemas

**Responsibility:** Define the ordered, replayable realtime envelope shared by task, model, tool, artifact, telemetry, network, security, and error streams. The payload is safe metadata only.

**Definitions:** `backend/app/events/contracts.py`

- `EventEnvelope(event_id, event_type, timestamp, project_id, task_id, execution_id, parent_id, component, status, payload, duration_ms, sequence_number)`
- `EventStatus` is `queued | in_progress | succeeded | failed | cancelled`.

**Reconciles:** Gap Analysis Sections 1, 8, 11, 15, 20, and 21. It adds the fields missing from the legacy `backend/app/events/envelope.py` without changing that compatibility class in Stage Three.

**Bypassing call sites to redirect later:**

- `backend/app/events/envelope.py:6-39` is the legacy envelope and lacks execution/parent/status/duration/sequence fields.
- `backend/app/agents/executor.py:125` publishes the legacy envelope.
- `backend/app/monitoring/sampler.py:64` publishes the legacy envelope for resource samples.
- `backend/app/realtime/router.py:16-30` streams the current event feed without replay/state synchronization.
- `backend/app/events/consumer.py` must later validate, sequence, and dead-letter malformed envelopes instead of leaving them pending.

## 8. Execution-Trace Schemas

**Responsibility:** Record safe, user-readable execution activity with bounded step/retry metadata and artifact references. The trace deliberately has `safe_summary` and no chain-of-thought field.

**Definitions:** `backend/app/agents/contracts.py`

- `ExecutionTraceEvent(event_id, task_id, execution_id, step_id, step_type, component, start_time, end_time, duration_ms, status, retry_number, parent_step_id, artifact_refs, error_category, safe_summary)`
- `ExecutionTraceSink.append(event) -> ExecutionTraceEvent`
- `ExecutionTraceSink.list_for_execution(execution_id) -> list[ExecutionTraceEvent]`

**Reconciles:** Gap Analysis Sections 3, 6, 8, 17, 20, 21, and 23. It creates the persistence/publication boundary needed to make the LangGraph lifecycle inspectable without exposing model reasoning.

**Bypassing call sites to redirect later:**

- `backend/app/agents/graph.py:58`, `:89`, and `:121` perform planning, tool execution, and evaluation without emitting durable trace events.
- `backend/app/agents/orchestrator.py:30-61` returns only a final dictionary and does not persist execution/step identity.
- `backend/app/events/publisher.py` and the legacy executor event path publish generic events but do not provide the trace schema or artifact references.

## Open Items Carried Forward

## Event Envelope Migration

Phase Four sovereignty audit events will emit **only the Phase 15 envelope** from `backend/app/events/contracts.py` on a dedicated `stream:sovereignty` stream. They will not be dual-emitted through the legacy envelope: dual emission would create duplicate audit counts and would make it impossible to tell whether a metric came from the application auditor or a legacy publisher.

The existing legacy envelope remains active for existing task, agent, tool, validation, system, and resource streams. Its current consumers are `backend/app/events/publisher.py`, `backend/app/events/consumer.py`, `backend/app/realtime/manager.py`, `backend/app/agents/executor.py`, and `backend/app/monitoring/sampler.py`; no frontend source is present in this workspace, so the documented consumer is the project WebSocket forwarding layer. The realtime manager will be extended to forward `stream:sovereignty` Phase 15 envelopes without converting them to the legacy shape.

Dropping legacy emission is a later coordinated migration decision, tracked by the checked-in constants in `backend/app/events/migration.py` (`PHASE15_SOVEREIGNTY_ENVELOPE_ONLY`, `LEGACY_EVENT_STREAMS_REMAIN_ACTIVE`, and `LEGACY_EVENT_RETIREMENT_STATUS`). Until all listed legacy consumers and external frontend consumers accept the Phase 15 envelope, legacy streams remain unchanged. The Stage Four auditor therefore has one authoritative emission path and does not silently broadcast both schemas.

For sovereignty accounting, `status: failed` has two distinct meanings until the envelope enum is revisited: a technical failure, or a policy-blocked-by-design network decision. Consumers must use `payload.decision` and `payload.destination_category` for blocked-request counts; they must not infer blocked traffic from envelope status or merge it into technical error totals.

## Pre-flight Decisions

- **Dependency declaration:** `PyJWT` and `python-docx` were already declared in `backend/requirements.txt` at inspection time, so duplicate declarations were not added. The Windows import path required `python-magic-bin==0.4.14`; the manifest now declares that Windows-specific package while retaining `python-magic>=0.4.27` for non-Windows environments. Verified local versions: `PyJWT 2.13.0`, `python-docx 1.2.0`, and `python-magic-bin 0.4.14`.
- **Paddle/OCR platform risk:** PaddleOCR imports `paddlepaddle` in `backend/app/workspace/parsers/registry.py` and `backend/app/tools/document_tools.py`. `paddlepaddle>=2.6.1` had no compatible distribution for the Windows development interpreter. This is not load-bearing for the telemetry stage; the placeholder decision is to scope PaddleOCR-dependent OCR demos to a supported Linux/container environment or replace the backend in Stage Seven after testing. See `docs/phase15/PLATFORM_NOTES.md`.

- The development database conflict remains open and belongs to Stage Eleven. `backend/tests/conftest.py` still creates metadata in the configured database; Stage Three intentionally does not alter test configuration, migrations, or fixtures.
- The worker/root/Docker-socket privilege conflict remains open for the later sandbox/security work.
- The legacy event envelope remains in place for compatibility until a later migration updates publisher, consumer, realtime replay, and existing tests together.
- No provider, adapter, registry implementation, executor implementation, network monitor, artifact store, persistence model, or orchestration behavior was added in this stage.

## Stage Three Status Report

**STAGE:** Three — Interfaces and Contracts  
**ENTRY CRITERIA MET:** Yes — `docs/phase15/GAP_ANALYSIS.md` exists and was read in full before inspection or edits. Its findings remain accurate; no contradiction was found.  
**WHAT WAS BUILT:** `docs/phase15/INTERFACE_CONTRACTS.md`; `backend/app/monitoring/contracts.py`; `backend/app/security/sovereignty.py`; `backend/app/models_ai/contracts.py`; `backend/app/tools/contracts.py`; `backend/app/artifacts/contracts.py`; `backend/app/events/contracts.py`; `backend/app/agents/contracts.py`.  
**TESTS ADDED:** `backend/tests/unit/test_phase15_contracts.py`, limited to imports, abstract method shape, required schema fields, explicit unavailable observations, provenance, and the absence of a reasoning field.  
**TEST RESULT:** Pass — `13 passed in 1.96s` from `venv\Scripts\python.exe -m pytest -q --confcutdir=backend/contract_tests backend/contract_tests/test_phase15_contracts.py`. The repository-wide test fixture was intentionally not used because it connects to the configured `db` host; that existing test-isolation conflict remains deferred to Stage Eleven.  
**DEVIATIONS FROM THE MASTER PROMPT:** The existing legacy `backend/app/events/envelope.py` was not replaced in this interface-only stage; the Phase 15 envelope is additive in `backend/app/events/contracts.py` so existing event publisher/consumer behavior is not silently changed before its coordinated migration. No concrete provider or adapter behavior was implemented.  
**CONFLICT RESOLUTION PROGRESS:**

- **Bypassed controls:** call sites are explicitly mapped above for telemetry (`monitoring/sampler.py:53`, `models_ai/resource_manager.py:43-48`, `monitoring/router.py`), network (`security/auth.py:20`, `models_ai/ollama_provider.py:21/80`, `sandbox/runner.py:31`), runtime/catalog (`agents/graph.py:43/58/121`, `models_ai/router.py:32/36/48-65`, `workspace/embedding_service.py:13/25`, `models_ai/registry.py`, `models_ai/resource_manager.py:77`), tools (`agents/graph.py:11/89`, `agents/orchestrator.py:13-26`, `agents/executor.py:23-40`), artifacts (`workspace/service.py:11-22`, `agents/graph.py:89`, `agents/orchestrator.py:30-61`), events (`events/envelope.py:6-39`, `agents/executor.py:125`, `monitoring/sampler.py:64`, `realtime/router.py:16-30`), and traces (`agents/graph.py:58/89/121`, `agents/orchestrator.py:30-61`). They are not fixed in Stage Three and are the routing checklist for Stages Four through Nine.
- **Dev DB in tests:** deferred to Stage Eleven and confirmed still open; `backend/tests/conftest.py` was not changed.

**OPEN QUESTIONS FOR THE HUMAN TEAM:** The Phase 15 envelope migration decision is resolved in the `Event Envelope Migration` heading and `backend/app/events/migration.py`. Remaining questions are the approved persistent catalog source, whether artifact content may be accepted as bytes at the service boundary or must be streamed, and the deployment privilege boundary for host/container monitoring and Docker sandbox control.  
**EXIT CRITERIA MET:** Yes — all eight areas have typed contracts and stubs; structural tests cover them; bypass call sites and the Stage Eleven database item are explicitly recorded; no concrete provider, adapter, executor, or persistence behavior was implemented.
