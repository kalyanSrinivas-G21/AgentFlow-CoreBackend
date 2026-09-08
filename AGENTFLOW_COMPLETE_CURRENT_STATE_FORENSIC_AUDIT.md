# AGENTFLOW COMPLETE CURRENT-STATE FORENSIC AUDIT

## 1. Executive Summary
A comprehensive forensic investigation of the AgentFlow project reveals a highly advanced, genuinely implemented agentic architecture targeting PS26117 compliance. The fundamental building blocks—including LangGraph agent orchestration, active local multi-model routing, isolated Docker-in-Docker sandboxing, and network sovereignty auditing—are firmly in place and correctly utilize physical constraints (VRAM, NVML, Redis outbox patterns). However, the implementation suffers from severe "Testing Reality" disparities: End-to-End (E2E) tests fail across the board due to architectural drift. The newly implemented LangGraph orchestrator (`app/agents/graph.py`) has superseded the legacy custom planner, yet several tests attempt to incorrectly mock legacy boundaries. Furthermore, testing assumes a background worker (`worker.main`) that is not spun up in test isolation, leading to task timeouts during Flagship Workflows.

## 2. Current Architecture
- **API/Routing:** FastAPI application (`app/main.py`) routing requests and managing the Redis Stream Consumer for real-time SSE updates.
- **Background Worker:** A dedicated Python process (`worker/main.py`) running a Redis Stream Consumer that retrieves `QUEUED` tasks and executes them via `TaskRunner`.
- **Database:** PostgreSQL with `pgvector` accessed via SQLAlchemy AsyncIO (`app/db.py`). Uses Alembic for migrations.
- **Event Bus:** Redis Streams implementing the Transactional Outbox pattern (`app/events/dispatcher.py`).
- **Orchestration:** LangGraph-based bounded state graph (`WorkflowGraph` in `app/agents/graph.py`) with plan -> execute -> observe -> reason loops.
- **Resource Manager:** Asynchronous NVML-based `GPUResourceManager` (`app/models_ai/resource_manager.py`) handling strict VRAM leasing and eviction.
- **Sandboxing:** Real Docker subprocess creation (`app/sandbox/runner.py`) using `ps26117-sandbox-base` with `--network=none` and tar-streamed file injections.

## 3. Capability Matrix
| Capability | Implementation Status | Evidence / Notes |
|------------|-----------------------|------------------|
| API Server | ✅ Real | `app/main.py` using FastAPI |
| DB Access | ✅ Real | Async SQLAlchemy (`app/db.py`) against `sovereign_ai` Postgres |
| Message Bus | ✅ Real | Redis Streams (`app/events/publisher.py`) |
| Agent Orchestration | ✅ Real | LangGraph implemented in `app/agents/graph.py` |
| Local LLM Inference | ✅ Real | `OllamaProvider` hitting `http://ollama:11434` |
| VRAM Management | ✅ Real | `GPUResourceManager` using `pynvml` |
| Execution Tracing | ✅ Real | `SqlAlchemyExecutionTraceSink` backing Postgres `execution_trace_records` |
| Tool Sandboxing | ✅ Real | `docker create` subprocess in `sandbox/runner.py` with `tmpfs` and `--network=none` |

## 4. PS26117 Compliance Matrix
| Requirement | Status | Evidence |
|-------------|--------|----------|
| Total Network Isolation | ✅ Compliant | Sandbox uses `--network=none` and drops all capabilities. |
| Multi-Model Routing | ✅ Compliant | `ModelRouter` selects based on capabilities and dynamically acquires VRAM leases. |
| Outbox Pattern | ✅ Compliant | Redis Stream outbox implemented and consumed by `worker.main`. |
| Sovereign Telemetry | ✅ Compliant | `ApplicationTelemetryAuditor` categorizes traffic against `TrustedNetworkPolicy`. |
| No Silent External Fallback | ✅ Compliant | Handled via exact model IDs and rigorous auditing; cloud fallback must be explicitly opted into. |

## 5. Phase 15 Stage Assessment
Phase 15 targets are structurally implemented but practically incomplete due to testing failures:
- **Implemented:** The unified telemetry interface, local AI service execution, VRAM lease locking, outbox patterns, and rigorous sandbox constraints.
- **Incomplete / Failing:** Verification through integration and E2E tests. The Flagship Workflow times out.

## 6. Architecture Integrity
The architecture is robust and heavily resilient. Real background loops handle lease recovery (`lease_recovery_loop` in `worker/main.py`) for abandoned tasks, and system components are strongly decoupled via Redis streams. The `GPUResourceManager` provides physical backpressure via `ResourceExhaustedError`, forcing standard retry mechanisms to handle resource scarcity naturally.

## 7. Mock / Simulation Audit
- **Unit Tests:** Rely correctly on `AsyncMock` and `MagicMock` (e.g., `test_agent_orchestrator.py`).
- **E2E Tests:** Overuse mocks incorrectly for legacy architecture (`orchestrator.planner.plan = AsyncMock(...)`), leading to false assertions or crashes when interacting with the modern `LangGraph` implementation.
- **Application Code:** **No simulated production behavior.** Local LLM inference truly hits Ollama, the Docker Sandbox truly spawns Docker containers, and VRAM management truly reads NVML data.

## 8. Security & Sovereignty Audit
- **ApplicationTelemetryAuditor:** Successfully intercepts application-level outbound requests (like `OllamaProvider` traffic).
- **Classification Engine:** Evaluates against `TrustedNetworkPolicy` (local AI, sandbox, loopback, internal infrastructure, cloud AI, external API).
- **Sandbox Confinement:** Blocks path traversal (`/`, `..`) and locks the container down with `--cap-drop=ALL` and `--security-opt=no-new-privileges:true`.

## 9. Real vs Mock Telemetry Audit
- **Hardware Telemetry:** Real `psutil` CPU/RAM metrics and `pynvml` GPU utilization are captured by the background `sample_resources` task in `app/monitoring/sampler.py`.
- **Model Usage Telemetry:** Traced natively to Postgres via `ExecutionTraceSink` emitting `ExecutionTraceEvent` objects.
- **Status:** **REAL**. No fake security metrics or hardcoded dashboards were found in the API layer.

## 10. Agentic Execution Audit
The legacy bespoke orchestrator was successfully replaced with LangGraph.
- **WorkflowGraph (`app/agents/graph.py`):** Drives a deterministic Plan -> Execute -> Observe -> Reason cycle.
- **Safety Boundaries:** Emits structured step events (`_trace`) and correctly respects `max_steps` and `max_retries` bounded execution limits. Implements an `approval_gate` mechanism for designated high-risk tools.

## 11. Multi-Model Audit
- **Registry:** `_REGISTRY` contains accurate quantization footprint estimates for `llama3.1:8b`, `qwen2.5-coder:7b`, `llava:7b`, and `nomic-embed-text`.
- **Router (`app/models_ai/router_v2.py`):** Automatically matches required capabilities (`["vision", "general"]`) against available models and rejects requests if no model has the capabilities or if health checks fail.

## 12. Resource Management Audit
- **Implementation:** `GPUResourceManager` (`app/models_ai/resource_manager.py`) is fully functional.
- **Admission Control:** Models must obtain a `ModelLease` which blocks if VRAM is exhausted, actively triggers eviction of idle models, and strictly enforces estimated VRAM ceilings to prevent OOM panics in the backend.

## 13. Flagship Workflow Audit
The flagship task (assign an abstract goal -> model creates plan -> executes in secure sandbox -> validates) is fully coded but currently **broken in testing environments**.
- `test_real_agent_workflow.py` fails with a timeout.
- **Root Cause:** The `worker.main` process (which dequeues `QUEUED` tasks and runs the agent graph) is completely absent in the `conftest.py` testing lifecycle, leaving tasks perpetually `QUEUED`.

## 14. Testing Reality
The project's test suite does not accurately reflect reality:
1. **Missing Test Worker:** `e2e` tests assume `docker-compose up` is running a live worker. Under local pytest execution, the `worker` process does not exist.
2. **Stale Mocks:** Several `e2e` tests (`test_slice4_sandbox_validation_loop.py`, `test_slice3_agent_writes_file.py`) heavily mock `orchestrator.planner.plan`, which is invalid under the new LangGraph paradigm.

## 15. Critical Risks (Ranked P0-P3)
- **[P0] E2E Test Suite Decay:** E2E tests fail universally due to obsolete mock injection and lack of a running worker fixture. This blocks verifiable CI/CD.
- **[P1] JWT Hardcoded Fallback:** Security `InsecureKeyLengthWarning` triggered by using a 31-byte development JWT key, technically violating minimum SHA256 requirements.

## 16. NEXT IMPLEMENTATION STAGE
The primary focus must be converging the E2E test suite with the physical architecture:
1. Migrate stale `e2e` tests targeting `AgentOrchestrator` to mock the LangGraph boundary (or invoke it cleanly).
2. Implement an in-process worker task in `conftest.py` during `pytest` runs to process the outbox queues natively, or refactor tests to explicitly execute the worker loop.

## 18. FINAL VERDICT
PS26117 READY: FALSE
PHASE 15 READY: FALSE
FLAGSHIP E2E READY: FALSE
SOVEREIGNTY PROOF READY: TRUE
PRODUCTION-DEMO READY: FALSE
CONFIDENCE: HIGH
NEXT AUTHORIZED ACTION: Fix E2E Test Mocking & Worker Spawn in conftest.py

## 19. SESSION HANDOFF
Investigation complete. The architecture is remarkably solid, properly constrained, and avoids hallucinating physical telemetry. The sole blockers preventing Phase 15 completion are misaligned End-to-End tests relying on deprecated mocks and a missing worker lifecycle in pytest. The next session must focus explicitly on test harness alignment.
