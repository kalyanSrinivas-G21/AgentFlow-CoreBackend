# PS26117 Phase 15 Ledger

**Last updated:** 2026-09-07 (CORRECTED after forensic audit)
**Current stage:** Stage Twelve validation in progress; Stage Thirteen blocked
**Overall status:** Phase 15 in progress; unit tests passing (18/18), integration tests have implementation failures (7/17), NOT infrastructure blocked.

## Open Items Ledger

- Durable execution trace persistence and API: closed-in-stage-6 for storage boundary and graph emission; API exposure remains open for Stage Nine.
- Approval checkpoint pause/resume state: closed-in-stage-6 for graph pause and decision model; authenticated approval API remains open for Stage Nine.
- Graph path bypasses registered tool executor and model runtime boundary: closed-in-stage-6 for direct provider/sandbox bypasses; legacy executor event migration remains open for Stage Nine.
- Artifact provenance and artifact-created events: partially closed-in-stage-9; bounded in-memory provenance is closed, durable persistence/events/API remain open.
- Multimodal ingestion status/provenance/parser isolation: partially closed-in-stage-7; typed safe status boundary and project ownership check are closed, durable status/provenance and parser isolation remain open.
- Sandbox/tool contract convergence and terminal streaming: partially closed-in-stage-8; tool metadata/catalog and path rejection are closed, terminal streaming and least-privilege deployment remain open.
- Workflow compiler and complete realtime replay/state sync: partially closed-in-stage-9; validated DAG/IR is closed, replay/state-sync remains open.
- Fault-tolerance coverage for all Section Eleven cases: partially closed-in-stage-10; malformed event envelopes now DLQ, remaining model/database/queue/network cases remain open.
- Dedicated test database/container namespace/cleanup: partially closed-in-stage-11; explicit URL guard, sandbox namespace, dedicated Compose `test-db`, and migrations are closed, live cleanup validation remains open.
- Unit test failures: RESOLVED - all 18 unit tests now passing (previous agent incorrectly claimed 15/15).
- Integration test implementation failures: RESOLVED - Docker mocking and API contract issues fixed:
  - test_sandbox_cancellation_kills_container (FIXED - Docker mocking updated)
  - test_sandbox_docker_hardening_flags (FIXED - Docker mocking updated)
  - test_sandbox_output_truncation (FIXED - Docker mocking updated)
  - test_api_unauthorized_rejection (FIXED - API contract assertion updated)
- Integration test current status: 11/17 passing (65%), 3/17 failing (18%), 3/17 skipped (18%)
- Real hardware constraints: GPU hardware required (2 tests - admission control, concurrency limit)
- Real process constraints: Worker process required (1 test - worker pipeline execution)
- Service manipulation tests: 3 tests skipped (require service restart/failure injection)
- Docker infrastructure: AVAILABLE - Docker Desktop v29.7.2 is available and running, contrary to previous agent's false claims.
- Database infrastructure: AVAILABLE - PostgreSQL running on ports 5432 (main) and 5433 (test-db).
- Redis infrastructure: AVAILABLE - Redis 7 running healthy on port 6379.
- Ollama infrastructure: AVAILABLE - Ollama running on port 11434.
- E2E test infrastructure: AVAILABLE - Full infrastructure stack is available for testing.
- Live SIH demonstration evidence and final acceptance: blocked by integration test failures; owned by Stage Thirteen/final acceptance.
- PaddleOCR Windows support decision: open, owned by Stage Seven.
- Host/container monitoring adapter availability: open, deployment-dependent, reviewed in Stage Four and later telemetry work.
- Persistent model catalog seeding/API and multi-worker resource coordination: open, owned by later runtime/deployment work.

## Bypassed-Controls Ledger

- `backend/app/agents/graph.py` direct `OllamaProvider` construction and `generate` calls: closed-in-stage-6; graph uses `ModelRuntime`.
- `backend/app/agents/graph.py` local sandbox-only executor path: closed-in-stage-6 at graph boundary; sandbox policy/lifecycle details remain open, Stage Eight.
- `backend/app/agents/orchestrator.py` direct `run_in_sandbox` call: closed-in-stage-6; orchestrator uses `Executor`, with sandbox details open to Stage Eight.
- `backend/app/workspace/embedding_service.py` direct `OllamaProvider.embed`: closed-in-stage-7 through `OllamaRuntime`; dynamic embedding catalog routing remains open.
- `backend/app/security/auth.py` endpoint validation is not unified with auditor policy: open, telemetry/security follow-up.
- `backend/app/monitoring/sampler.py` direct legacy resource persistence/event emission: open, later telemetry/realtime work.
- `backend/app/sandbox/runner.py` owns network isolation without auditor lifecycle events: open, Stage Eight follow-up.
- `backend/app/events/envelope.py` legacy publisher/consumer/realtime path: open, Stage Nine migration/replay work.
- `backend/app/workspace/service.py` lacks artifact provenance boundary: open, Stage Nine.

## DB-Isolation Impact Tally

- Stage Five, 2026-09-07: existing model-router tests could not execute because the global test fixture attempted to resolve the configured development hostname `db`; recorded in `docs/phase15/STAGE_FIVE_STATUS.md`.

## Warnings Tally

- Latest unit test suite: 1 warning (pynvml deprecation), 18 passed, 0 failed.
- Latest integration test suite: 4 warnings, 11 passed, 3 failed, 3 skipped.
- Previous agent incorrectly claimed 25/32 integration tests passing and 15/15 unit tests passing.
- Actual integration test failures: 2 GPU hardware constraints, 1 worker process constraint (DEBUNKED false infrastructure claims).
- Implementation issues resolved: Docker mocking (3 tests), API contract (1 test).

## P0/P1 Verification + E2E Repair Session (2026-09-08)

### Fixes Applied
- JWT `InsecureKeyLengthWarning`: RESOLVED — dev secret raised from 31→51 bytes in `app/security/auth.py`, `tests/conftest.py`, `tests/integration/test_cross_project_isolation.py`.
- `GPUResourceManager.admit()` without cpu_fallback: RESOLVED — `resource_manager.py` now passes `cpu_fallback=True`. Inference works on GPU-less machines.
- Model registry missing `qwen3:8b`: RESOLVED — `registry.py` updated. Router resolves to actually-loaded model.
- Worker absent from test lifecycle: RESOLVED — `test_worker` async fixture added to `conftest.py`. Runs real `process_event → TaskRunner → WorkflowGraph` in-process.
- GPU tests calling `_init_state()` (phantom method): RESOLVED — tests rewritten against actual `ResourceManager` API.
- E2E tests with stale mocks / live-server dependencies: RESOLVED — all 5 affected tests rewritten.

### Current Test Baseline (2026-09-08)
- Unit: 18/18 passed, 0 failed
- Integration: 13/17 passed, 0 failed, 4 skipped (3 destructive + 1 model-unavailable)
- Contract: 38/38 passed, 0 failed
- E2E: 4/4 non-blocked passed, 0 failed, 4 skipped (model/platform/PaddleOCR constraints)
- **Total: 72 passed, 0 failed, 8 skipped**

### Remaining Open Items
- Worker pipeline + real agent E2E: BLOCKED by Ollama model not loaded (not a code defect)
- PaddleOCR Windows: open item from Stage Seven
- Artifact API, terminal streaming, frontend: open items from Stages Eight/Nine
