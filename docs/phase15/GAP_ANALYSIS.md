# PS26117 Phase 15 Gap Analysis

**Inspection date:** 2026-09-07  
**Baseline:** repository as inspected before Phase 15 implementation changes  
**Status:** Stage Zero reconnaissance complete; Phase 15 implementation remains in progress.

## Scope and Evidence

The repository is a Python 3.11 FastAPI application with PostgreSQL/pgvector, Redis Streams, Ollama, a worker process, LangGraph orchestration, Docker sandbox execution, JWT project membership, and a WebSocket event feed. Primary evidence inspected:

- `backend/app/` modules for models, orchestration, tools, workspace, sandbox, monitoring, events, and realtime transport.
- `backend/tests/` unit, integration, and E2E tests.
- `backend/alembic/versions/` migrations, `docker-compose.yml`, `backend/worker/main.py`, `README.md`, `docs/`, and `IMPLEMENTATION_REPORT.md`.
- The clean validation report records `25 passed, 4 skipped, 13 failed`; therefore the existing implementation is not acceptance-clean.

Status labels below are deliberately conservative:

- **Already exists:** implemented behavior was found in the inspected code.
- **Partially exists:** a related foundation exists, but the master-prompt contract is incomplete.
- **Does not exist:** no implementation or contract was found.
- **Conflicts:** existing behavior actively disagrees with a requirement; the proposed resolution is recorded rather than silently choosing a side.

## Executive Baseline

The repository has credible foundations: transactional PostgreSQL events and outbox delivery, Redis consumer groups and leases, LangGraph planning/execution scaffolding, local Ollama generation and embeddings, pgvector chunks, JWT project checks, workspace containment checks, and a restrictive Docker sandbox. The defining Phase 15 gaps are truthful sovereignty/network telemetry, persistent multi-model runtime management, durable safe execution traces, artifact provenance, workflow compilation, terminal streaming, complete failure semantics, and test isolation.

The central architectural conflict is that the newer LangGraph path does not consistently use the existing registered-tool executor, event/trace path, artifact path, or approval path. Phase 15 should converge those paths instead of introducing parallel subsystems. The other hard conflict is operational: the worker has Docker socket access and runs as root, while the prompt requires least privilege and no unnecessary host privileges. The resolution must preserve sandbox capability while moving privilege into a narrowly scoped deployment boundary or explicitly documenting the deployment limitation.

## Section-by-Section Analysis

### 1. Sovereignty and Local Execution Verification

- **Already exists:** `security/auth.py` validates configured Ollama endpoints; application resource sampling exists in `monitoring/sampler.py`; sandbox networking uses Docker `--network=none`; an HTTPX monkeypatch test checks external egress behavior.
- **Partially exists:** application-level local endpoint policy and resource snapshots provide a starting adapter, but there is no authoritative monitoring capability state or metadata source/confidence model.
- **Does not exist:** Sovereignty Auditor interface and platform adapters, configurable trusted-network classification, audit event model, `/api/v1/sovereignty/metrics`, data-transfer accounting, blocked/unknown external state, or real-time sovereignty stream.
- **Conflicts:** `validate_local_endpoint()` constrains selected Ollama URLs but does not observe or enforce all application egress. `docs/demo_script.md` describes live/air-gapped evidence the implementation cannot currently prove. Resolve by reporting application-level or limited monitoring honestly and adding adapters incrementally; infrastructure firewall enforcement must remain outside application startup.

### 2. Local Multi-Model Runtime

- **Already exists:** `models_ai/registry.py` contains a static capability registry; `ollama_provider.py` supports generation, embeddings, structured generation, and streaming; `resource_manager.py` reads NVML when available and limits concurrency.
- **Partially exists:** `ModelRouter` selects by a small capability/fallback mapping and the resource manager admits models by static VRAM estimates.
- **Does not exist:** persistent model catalog, provider-specific load/unload/status/health/resource adapters, runtime health state machine, bounded swap queue, cancellation/progress states, reference-counted active inference tracking, or explicit CPU fallback policy.
- **Conflicts:** unknown models are admitted blindly; model eviction can occur without active-request reference tracking; insufficient resources are rejected despite messaging that suggests queueing; model names/capabilities are hardcoded. Resolve by introducing interfaces first, then making admission fail closed for unknown resource requirements and keeping cloud fallback disabled by default.

### 3. Agentic Orchestration Core

- **Already exists:** `agents/graph.py` provides LangGraph plan, execute, observe, and reason nodes; `agents/orchestrator.py` bounds iterations and uses local model planning.
- **Partially exists:** there is a real state machine and replanning loop, but the state does not cover the full required lifecycle and persistence is not connected to trace/artifact/approval records.
- **Does not exist:** durable Agent Execution Trace API/model, execution IDs and step metadata, artifact/completion nodes, approval pause/resume state, and uniform cancellation/resource budgets.
- **Conflicts:** the graph executor recognizes only `sandbox` and bypasses the registered `Executor` policy/schema/audit path. Planner failure becomes an empty plan, and `step_count` measures planning iterations rather than actual bounded work. Resolve by routing graph tool calls through the registered executor and emitting safe trace events, never model reasoning.

### 4. Multimodal Document and Knowledge Processing

- **Already exists:** parsers for DOCX, XLSX, CSV/text, PDF, and images in `workspace/parsers/registry.py`; optional PaddleOCR; Ollama embeddings and pgvector chunks; project filtering during retrieval.
- **Partially exists:** local parsing, embedding, and retrieval are present, but provenance, ingestion lifecycle, and model routing are incomplete.
- **Does not exist:** durable Pending/Processing/Completed/Partially Processed/Failed/Unprocessable status model, isolated parser worker, page/section source metadata, ingestion failure events, and fully dynamic embedding/VLM selection.
- **Conflicts:** risky parsing runs synchronously inside backend tool execution; ingestion does not prove `file_id` belongs to the project before embedding; fixed character slicing loses provenance. Resolve with project ownership validation at ingestion, durable status, bounded parser isolation, and source-aware chunks.

### 5. Tool Execution and Sandboxing

- **Already exists:** registered tools, Pydantic validation, policy checks, timeout handling, normalized results in `tools/base.py`, `tools/policy.py`, and `agents/executor.py`; Docker sandbox has no network, read-only root, CPU/memory/PID limits, dropped capabilities, no-new-privileges, output bounds, and cancellation cleanup.
- **Partially exists:** the contract is strong for the legacy executor and sandbox, but tool health, resource budgets, configurable network policy, approvals, and streamable lifecycle telemetry are missing.
- **Does not exist:** a single registry contract used by all orchestration paths with execution environment, task capabilities, health, and approval metadata.
- **Conflicts:** LangGraph uses a separate sandbox-only executor and bypasses registry/policy/schema/audit handling. Compose gives the worker root plus Docker socket access. Resolve by converging execution through `agents/executor.py` and isolating privileged sandbox control into the smallest deployable boundary.

### 6. Artifact Management and Real Deliverables

- **Already exists:** an `artifacts` table existed in the initial migration.
- **Partially exists:** workspace file storage can hold files, but no task/step provenance is attached.
- **Does not exist:** current artifact ORM/service/routes, artifact-created event, preview/download contract, artifact discovery, or orchestration artifact-generation step; a later migration removes the initial artifacts table.
- **Conflicts:** the current system can execute work without producing a durable deliverable, contrary to the acceptance scenario. Resolve by restoring a deliberate artifact model/migration and making artifact creation a typed, traceable capability.

### 7. Workflow Orchestration and Canvas Compatibility

- **Already exists:** `WorkflowGraph` is an internal LangGraph execution graph.
- **Partially exists:** graph execution is bounded, but it is not a frontend workflow-definition compiler.
- **Does not exist:** validated node/edge schemas, intermediate representation, tool/model reference checks, graph-size/cycle policies, workflow routes, persistence, or deterministic node execution records.
- **Conflicts:** an internal agent graph must not be treated as acceptance of arbitrary frontend graphs. Resolve by adding a strict compiler whose IR maps only to registered capabilities and rejects arbitrary code/configuration.

### 8. Real-Time Frontend-Backend Contracts

- **Already exists:** PostgreSQL event plus outbox persistence, Redis Streams/consumer groups, project WebSocket rooms, JWT project checks, and model-token SSE.
- **Partially exists:** `events/envelope.py` provides identity, causation, payload, and schema version, but not the complete Phase 15 envelope or replay semantics.
- **Does not exist:** required `execution_id`, `parent_id`, `status`, `duration`, `sequence_number`, replay/state-sync, and complete model/resource/network/security/VRAM event coverage.
- **Conflicts:** WebSocket consumers begin at Redis `$`, so prior events are lost; malformed messages can escape handling; JWT is carried in a query string. Resolve with durable sequence/replay or snapshot synchronization, poison-message handling, and document the browser-compatible auth trade-off while reducing token exposure where possible.

### 9. Workspace and File System Management

- **Already exists:** canonical project-root resolution, absolute-path rejection, traversal checks, and symlink-aware containment in `workspace/service.py`; upload size and MIME checks.
- **Partially exists:** path containment is sound locally, but project existence/membership is not enforced by `get_project_dir`, and file operations are incomplete.
- **Does not exist:** complete list/tree/create/read/write/rename/move/delete/artifact APIs, durable ingestion metadata, and protected-directory approval controls.
- **Conflicts:** `get_project_dir()` creates any requested project directory, so a caller reaching this service can create/access a non-existent project unless every caller separately checks membership. Resolve by requiring an authorized project context before directory creation and centralizing all operations behind it.

### 10. Real-Time Terminal and Sandbox Output

- **Already exists:** sandbox captures bounded stdout/stderr and supports cancellation cleanup; model tokens use SSE.
- **Partially exists:** output exists as a completed `SandboxResult`, not a controlled live terminal channel.
- **Does not exist:** authenticated sandbox-terminal WebSocket/SSE, task/sandbox binding, cursors/reconnect, cancellation endpoint, and cleanup contract exposed to clients.
- **Conflicts:** the existing project WebSocket is an event feed, not host-safe terminal streaming. Resolve by adding a sandbox-only stream with project/task authorization and bounded output; never expose the host shell.

### 11. Edge Case Resiliency

- **Already exists:** transactional outbox, Redis idempotency/leases/DLQ foundations, expired-task recovery, sandbox timeout/cancellation cleanup, and physical failure-injection tests.
- **Partially exists:** worker recovery and infrastructure failure handling cover portions of poison messages, queue failure, and sandbox failure, but structured-output, model-health, database saturation, GPU, approval, and network-partition semantics are incomplete.
- **Does not exist:** bounded structured-output repair, runtime health/recovery state machine, durable approval recovery, explicit database pool saturation policy, and distinct network failure/security states.
- **Conflicts:** malformed event validation can leave messages pending; resource manager can claim queue behavior while rejecting immediately; local model failure has no guaranteed local fallback path. Resolve with explicit bounded state transitions and tests for all seven sub-cases.

### 12. Test Isolation and Development Reliability

- **Already exists:** ORM imports and async engine disposal were improved; integration tests can exercise real Compose services and physical failure paths.
- **Partially exists:** teardown disposes the engine, but the configured database remains the target and sandbox names are random without a tracked test namespace.
- **Does not exist:** dedicated test database lifecycle, migration-based test setup/cleanup, controlled test container/network/volume labels, and guaranteed cleanup independent of test outcome.
- **Conflicts:** `tests/conftest.py` creates metadata in the configured database, which can be the primary development database; destructive tests stop shared Compose services. Resolve with an explicit test-only database/service namespace and guarded destructive fixtures.

### 13. Resource Telemetry

- **Already exists:** `monitoring/sampler.py` and `models_ai/resource_manager.py` sample CPU, memory, GPU utilization, active tasks, and NVML VRAM when available.
- **Partially exists:** latest snapshots can be persisted and exposed, but source, confidence, availability state, per-model usage, queue depth, inference/tool activity, and network counters are absent.
- **Does not exist:** typed Resource Telemetry Interface and provider set for CPU/GPU/memory/runtime/network, bounded historical samples, and explicit development-mock provider labeling.
- **Conflicts:** unavailable GPU values are represented as zeros in resource-manager responses, which can be mistaken for measured zero. Resolve with a typed observation state (`measured`, `not_observed`, `unavailable`, `blocked`, etc.) and source metadata.

### 14. Monitoring Page Data Contract

- **Already exists:** authenticated `/api/v1/metrics/latest` and Prometheus `/metrics` endpoints for a small resource snapshot.
- **Partially exists:** the API can support a monitoring page for CPU/memory/GPU/task count, but not a sovereignty evidence surface.
- **Does not exist:** monitoring contract for model/tool/agent activity, VRAM, local/external/cloud/blocked requests, data transfer, security policy, capability state, or distinct observation states.
- **Conflicts:** the current API has no way to distinguish measured zero from unavailable and defaults missing GPU data to zero-like fields. Resolve by returning typed observations and honest capability/security states; do not synthesize zeros.

### 15. Graph and Telemetry Presentation Support

- **Already exists:** database timestamped resource rows and a Prometheus latest snapshot.
- **Partially exists:** persistence is a starting point for time-series retrieval, but there are no metric-name/unit/source/confidence records or rolling windows.
- **Does not exist:** bounded time-series API, one-minute/five-minute/thirty-minute/session windows, aggregation policy, and telemetry event payload contract for chart consumers.
- **Conflicts:** latest-only data cannot support causal live graphs or bounded historical views. Resolve with bounded samples and server-side window/aggregation semantics; frontend animation must not manufacture data.

### 16. Security Model

- **Already exists:** JWT authentication, project membership checks on REST/WebSocket paths, metadata-oriented audit records, path containment, and sandbox restrictions.
- **Partially exists:** deployment modes and secrets are conceptually configurable through environment variables, but secure defaults and privilege separation are incomplete.
- **Does not exist:** explicit development/demo/secure-local/enterprise guarantee profiles, secret rotation/management contract, immutable audit posture, protected workspace approval model, and separated monitoring privilege boundary.
- **Conflicts:** Compose hardcodes database credentials, demo token, and a weak/default JWT fallback; the worker runs as root with Docker socket access. Resolve by removing production secrets/defaults, documenting development-only defaults, and redesigning sandbox control permissions before claiming least privilege.

### 17. PS26117 Demonstration Flow Support

- **Already exists:** local document parsing/embeddings, task APIs, local model access, LangGraph scaffolding, tools, sandbox, event delivery, and resource snapshots can demonstrate fragments of the flow.
- **Partially exists:** a document-to-local-model-to-tool path is plausible, but it is not a durable, observable, artifact-producing end-to-end workflow.
- **Does not exist:** proven causal monitoring updates, artifact event/delivery, complete trace, model-per-capability selection, and a repeatable acceptance fixture.
- **Conflicts:** `docs/demo_script.md` overstates air-gapped/live observability compared with available evidence. Resolve by implementing and executing a documented local scenario, and revise demo claims to match the measured deployment mode.

### 18. No Fake Sovereignty

- **Already exists:** local Ollama endpoint validation and Docker sandbox network isolation avoid some obvious egress paths; the report documents local-first intent.
- **Partially exists:** application-level local request policy is real, but it does not measure all network activity and missing telemetry is sometimes represented as zero/unavailable fields.
- **Does not exist:** source-labelled real network audit, blocked-request evidence, cloud-AI observation status, and API/UI disclosure of mock versus measured values.
- **Conflicts:** static or zero-like values from missing telemetry could be interpreted as proof of no external traffic; demo language claims more than instrumentation proves. Resolve by fail-closed classification where applicable and use `not_observed`/`unavailable` rather than zero.

### 19. Performance and Concurrency

- **Already exists:** async FastAPI/worker paths, Redis leases, bounded sandbox output, task retry foundations, LangGraph iteration cap, and a basic inference concurrency limit.
- **Partially exists:** some operations have timeouts and cancellation, but model queues, event queues, resource budgets, and all long-running paths are not bounded consistently.
- **Does not exist:** bounded model swap queue with progress/cancellation, bounded WebSocket buffering/replay policy, comprehensive task resource budgets, and uniform timeout/cancellation contracts.
- **Conflicts:** model admission raises “queued” errors rather than providing a bounded queue; model loading/unloading uses assumptions and lacks active-request-safe eviction. Resolve with async primitives and explicit queue state, never sleep-based synchronization.

### 20. Observability

- **Already exists:** Python logging, audit records, event correlation/causation fields, task IDs, and some worker lifecycle events.
- **Partially exists:** correlation is present in events but not threaded consistently through logs, model/tool/runtime operations, and safe frontend error responses.
- **Does not exist:** standardized error categories across services, structured log schema, execution IDs/model IDs/tool IDs on every relevant line, and server-side diagnostic retention policy.
- **Conflicts:** orchestrator returns raw exception text in its error payload and planner failures are flattened to empty plans, weakening diagnosis and user-safe semantics. Resolve with categorized internal errors and safe external summaries.

### 21. API Design Requirements

- **Already exists:** versioned task/project/model chat routes, Pydantic request/response validation, JWT protection, and generated OpenAPI artifacts.
- **Partially exists:** model, task, workspace, event, and monitoring contracts exist at different maturity levels.
- **Does not exist:** versioned workflow, artifact, approval, sovereignty, terminal, execution-trace, model-runtime-management, and complete telemetry API groups.
- **Conflicts:** `/api/v1/metrics/latest` is not the required monitoring/sovereignty contract, and realtime event fields do not match the master envelope. Resolve by extending existing route groups and schemas rather than duplicating service layers.

### 22. Implementation Order

- **Already exists:** prior phases provide a staged architecture and `IMPLEMENTATION_REPORT.md` records earlier validation work.
- **Partially exists:** the repository has foundations from stages before Phase 15, but no Phase 15 Stage Zero artifact existed at inspection start and no stage reports for stages three through thirteen were found.
- **Does not exist:** the required `docs/phase15/GAP_ANALYSIS.md` before this work, per-stage entry/exit evidence, and one-reviewable-diff discipline for the remaining stages.
- **Conflicts:** the Phase 14 report calls the architecture conditionally ready while recording 13 test failures and substantial Phase 15 contract gaps. Resolve by treating this document as the baseline and keeping Phase 15 explicitly in progress until exit criteria are evidenced.

### 23. End-to-End Acceptance Scenario

- **Already exists:** each major ingredient exists in isolation: task lifecycle, local model calls, document parsing, retrieval, tools, sandbox, events, and workspace storage.
- **Partially exists:** integration tests and demo documentation exercise portions, but local model dependencies may be skipped and no single scenario verifies causal telemetry plus artifact provenance.
- **Does not exist:** a passing complete confidential-work acceptance run with plan, local routing, local processing, retrieval, controlled tool, validation, artifact, trace, and simultaneous monitoring evidence.
- **Conflicts:** the current test result is not clean and the report’s readiness language exceeds the demonstrated acceptance evidence. Resolve by creating a deterministic local fixture/runtime profile and attaching actual outputs and API responses to the final report.

### 24. Strict Engineering Requirements

- **Already exists:** typed Pydantic models, async services, project auth, path checks, local endpoint policy, Docker restrictions, transactional outbox, and several bounded loops/timeouts.
- **Partially exists:** incremental architecture is present, but implementation paths are duplicated and several defaults assume privileged/shared infrastructure.
- **Does not exist:** complete dynamic model catalog, truthful telemetry state model, unified tool/trace/artifact contracts, comprehensive failure tests, and no-secret deployment baseline.
- **Conflicts:** hardcoded model registry, default credentials/tokens, root Docker-socket worker, raw error leakage, blind unknown-model admission, and stale failing tests violate explicit requirements. Resolve each in the stage order; do not paper over failures by skipping tests or labelling mocks as production telemetry.

### 25. Final Definition of Success

- **Already exists:** a credible partial foundation for local inference, project isolation, bounded sandboxing, event durability, and hardware-aware admission.
- **Partially exists:** the system can perform pieces of confidential enterprise work, but not yet with complete multi-model runtime management, durable agent traces, artifacts, workflow compilation, real sovereignty evidence, or acceptance-grade recovery.
- **Does not exist:** simultaneous satisfaction of all Phase 15 requirements, all thirteen stage exit reports, seven edge-case failure demonstrations, complete acceptance evidence, and final updated gap analysis.
- **Conflicts:** current documentation and status cannot honestly claim Phase 15 completion while tests fail and the required monitoring distinctions are absent. Resolution: status remains **Phase 15 in progress** until the final definition is evidenced, not asserted.

## Proposed Resolution Order

1. Stage Three: lock the shared typed contracts and observation-state vocabulary without implementing behavior prematurely.
2. Stage Four: add application-level sovereignty auditing first, then platform/container adapters only where capabilities are real; expose unavailable/limited states.
3. Stage Five: replace blind static admission with persistent catalog/runtime interfaces and bounded resource scheduling.
4. Stage Six: converge LangGraph with the registered executor, durable execution trace, safe retries, approvals, and artifact hooks.
5. Stages Seven through Nine: add durable ingestion, artifact management, workflow compiler, and complete realtime/replay contracts.
6. Stages Ten through Eleven: close failure semantics and test isolation before broad integration runs.
7. Stages Twelve and Thirteen: run the clean integration suite and attach a real acceptance demonstration, including measured API responses and honest limitations.

## Stage Zero Status Report

**STAGE:** Zero — Repository Reconnaissance and Gap Analysis  
**ENTRY CRITERIA MET:** Yes. The master prompt was read from disk in full; backend modules, tests, migrations, worker, sandbox, monitoring, realtime, deployment, and existing reports were inspected.  
**WHAT WAS BUILT:** This gap analysis at `docs/phase15/GAP_ANALYSIS.md`.  
**TESTS ADDED:** None. Stage Zero is documentation-only; no implementation code was changed.  
**TEST RESULT:** Not applicable. The existing validation baseline remains `25 passed, 4 skipped, 13 failed` as recorded in `IMPLEMENTATION_REPORT.md`; it is not being re-run as part of reconnaissance.  
**DEVIATIONS FROM THE MASTER PROMPT:** None for Stage Zero. The repository is explicitly marked as not Phase 15 complete.  
**OPEN QUESTIONS FOR THE HUMAN TEAM:** Confirm the intended deployment privilege boundary for Docker sandbox control; confirm whether enterprise deployments provide host/container network telemetry privileges; confirm the approved local model runtime/catalog persistence source; confirm whether the existing frontend expects WebSocket replay or can adopt a state-sync contract.  
**EXIT CRITERIA MET:** Yes. The required pre-implementation gap analysis exists and is the baseline for subsequent stages.
