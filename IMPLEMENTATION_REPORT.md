# ProjectSovereign On-Premise Agentic AI Workbench
## Final Architecture Validation and Comprehensive Implementation Report

**Project:** PS26117
**Validation phase:** Phase 14, Steps 14.1-14.14
**Validation date:** 2026-09-07
**Validation environment:** Windows host, Docker Compose, Python 3.11.16, PostgreSQL/pgvector, Redis 7, Ollama

## 1. Original Finding

The original audit assessed the prototype at 3.0/10. The central runtime was not dependable: circular imports and mismatched ORM fields involving `AgentRun` and `PlanStep` prevented a stable execution path. Security was based on one shared bearer token, with no project-level tenant isolation. GPU use was effectively unmanaged, creating a predictable out-of-memory risk on the target 6 GB hardware.

The prototype also routed document work inefficiently. Native text formats and images were treated alike, causing unnecessary use of a large vision-language model. Event publication was non-atomic: the database write and Redis write could diverge if Redis failed. Cancellation was only a database status update and did not terminate active work. The previous verification further overstated readiness because nominal E2E tests were mock-heavy and did not prove recovery from physical Redis, worker, or sandbox failures.

## 2. Root Causes

The root causes were missing ownership boundaries and optimistic infrastructure assumptions:

- Domain models, execution logic, transport code, and persistence were coupled closely enough for import cycles and ORM drift to break startup.
- The system treated Redis as part of the request transaction even though PostgreSQL was the durable authority.
- Tasks had no reliable lease/recovery protocol, so a worker crash could strand work in `RUNNING`.
- A single token could not identify a user, project membership, or authorization scope.
- Inference admission assumed that model memory requirements would fit the machine instead of measuring available VRAM.
- Raw LLM output was allowed too close to tool execution. There was no consistent schema and policy boundary between planning and side effects.
- Sandbox execution depended on host/container filesystem assumptions that were not valid when the Docker daemon was outside the backend container.
- Tests created metadata incompletely and reused pooled asyncpg connections across pytest event loops, hiding clean-deployment defects until the volume was wiped.

## 3. Implemented Fixes

The remediation journey implemented the following phase outcomes:

1. **Phases 1-3, runtime and topology:** Stabilized module boundaries, separated API and worker containers, and established PostgreSQL, Redis, Ollama, backend, and worker Compose services.
2. **Transactional events:** `backend/app/events/publisher.py` writes an authoritative `EventRecord` and an `OutboxEvent` in one PostgreSQL transaction. The dispatcher later forwards unprocessed rows to Redis Streams.
3. **Phase 4, LangGraph:** `backend/app/agents/graph.py` uses a LangGraph `StateGraph` with plan, execute, observe, and reason nodes. The state machine can re-plan from tool observations and caps iterations.
4. **Phases 5-7, tool and model safety:** Tool calls pass registry lookup, policy checks, Pydantic input validation, bounded execution, and normalized `ToolResult` handling. `ModelRouter` selects models by capabilities and fallback chains.
5. **Phase 8, document intelligence:** Native DOCX, CSV, and XLSX parsing and PaddleOCR avoid sending ordinary text to a VLM. Embeddings and document chunks remain project-scoped.
6. **Phase 9, hardware admission:** `backend/app/models_ai/resource_manager.py` uses NVML telemetry, concurrency limits, model VRAM estimates, model unload behavior, and a safety buffer before admitting inference.
7. **Phase 10, streaming and cancellation:** LLM tokens are exposed through SSE. Async cancellation propagates to active tasks and Docker sandbox processes.
8. **Phase 11, identity and authorization:** JWT validation replaced the shared token model. REST project routes verify `ProjectMember` membership, and WebSockets validate the same project boundary.
9. **Phases 12-13, verification and contracts:** Physical failure-injection tests cover Redis outage, worker lease recovery, and sandbox timeout. OpenAPI and event documentation provide frontend-facing contracts.
10. **Phase 14 clean-state corrections:** The initial clean run found that pgvector was not bootstrapped before `VECTOR(768)` metadata creation. The initial migration and test bootstrap now execute `CREATE EXTENSION IF NOT EXISTS vector`. The global async engine now uses `NullPool` to avoid cross-event-loop asyncpg connection reuse. Test metadata imports now include agent, tool, and event models so all foreign-key targets are registered.

## 4. Architectural Impact

The system moved from a monolithic prototype toward an event-driven service topology:

```text
Client
  -> FastAPI backend
       -> PostgreSQL transaction: task/event/outbox authority
       -> Redis Streams: asynchronous delivery
            -> Worker consumer
                 -> lease claim
                 -> LangGraph orchestration
                 -> policy/schema/tool boundary
                 -> Docker sandbox or local Ollama
       -> realtime Redis tailer
            -> project-filtered WebSocket broadcast
       -> SSE model stream
```

PostgreSQL is the source of truth for tasks, audit events, leases, projects, memberships, and outbox rows. Redis is a delivery and coordination layer, not the durable request transaction. `OutboxEvent.processed` remains false when Redis is unavailable, allowing a later dispatcher pass to retry delivery.

Worker task claims use an atomic update that accepts `QUEUED` work or expired `RUNNING` leases. The worker recovery loop scans expired leases and republishes a queued event. This closes the physical worker-crash gap tested in Phase 12. The design is still single-node at the infrastructure level: Redis, PostgreSQL, and the worker are not clustered.

## 5. Tests Added

The repository now includes physical failure-injection coverage in `backend/tests/integration/test_failure_modes.py`:

- **Redis outage:** Stops the real Compose Redis container, commits an event and outbox row to PostgreSQL, and verifies the row remains unprocessed.
- **Worker crash:** Stops the real worker container, inserts an expired `RUNNING` task, restarts the worker, and verifies a new worker identity reclaims the task with an increased attempt count.
- **Sandbox timeout:** Runs an infinite loop in the actual Docker sandbox, verifies a controlled `timeout` result, and verifies no `sandbox_*` container remains.

The sandbox runner also had to be made Docker-daemon independent: input files are archived and streamed into an isolated workspace tmpfs rather than relying on a temporary host path visible to a different Docker daemon namespace. The container has no network, a read-only root, bounded memory/CPU/PIDs, dropped capabilities, and output truncation.

The clean-suite run also exposed and corrected test bootstrap gaps: pgvector extension creation, complete ORM registration, and asyncpg pool lifecycle. These checks distinguish physical deployment defects from pure unit-test success.

## 6. Verification Result

The requested physical sequence was executed:

```text
docker compose down -v
```

Result: all five service containers, both named volumes, and the Compose network were removed.

```text
docker compose up --build -d
```

Result: backend and worker images rebuilt; new PostgreSQL and Ollama volumes were created; Redis and PostgreSQL became healthy; Ollama, worker, and backend started.

The first clean test pass reached an infrastructure failure because the test metadata omitted ORM imports. After fixing the bootstrap, the complete suite reached application behavior:

```text
25 passed, 4 skipped, 13 failed, 11 warnings in 117.31s
```

The clean validation therefore does **not** meet the requested 100% pass criterion. The failing tests are:

- Agent workflow result contract: BANANA output was not present.
- Slice 2 REST E2E: unauthenticated legacy test request.
- Slice 3 tool executor: stale `repo` expectation.
- Slice 4 sandbox/validation tests: stale `ToolResult` and orchestrator contracts.
- Cancellation test: incompatible subprocess mock awaitability.
- Unauthorized response wording mismatch.
- Sandbox hardening/output tests: mocks assume the old `docker run` invocation shape.
- Worker pipeline timeout.
- Agent orchestrator unit tests: stale `planner` attribute and legacy planner expectations.

The clean run proves the environment can build and boot from wiped state and that 25 tests pass, but it does not prove full repository readiness. The result must be treated as a remediation checkpoint, not a final 100% acceptance result.

## 7. Remaining Gaps

The immediate remaining gap is test/application contract convergence. The LangGraph orchestrator has replaced the legacy `planner` attribute expected by several unit tests, but those tests were not migrated to mock the graph boundary. Sandbox tests still mock the former subprocess shape, while the physical runner now uses `docker create` and `docker start -a -i` to support Docker-in-Docker file transfer.

The unauthenticated Slice 2 test conflicts with the mandatory JWT design and needs a valid project member plus a Bearer token. The worker pipeline timeout needs investigation against the fresh Ollama/model state and worker logs. The agent E2E assertion needs a deterministic tool-result contract or a test fixture that controls the local model response.

The final report is intentionally not declaring Phase 14 complete until those failures are resolved and a subsequent clean run reports zero failures.

## 8. Known Limitations

- Docker-in-Docker remains operationally sensitive to daemon visibility, image availability, and socket permissions. The runner now avoids host-path bind assumptions, but it still requires access to `/var/run/docker.sock` and the `ps26117-sandbox-base` image.
- Redis is a single-node delivery bottleneck and has no Sentinel or cluster failover.
- PostgreSQL is single-node in Compose and has no configured backup, replication, or point-in-time recovery.
- Worker recovery is lease-based. A task can wait for the recovery interval and lease expiry before reprocessing.
- The current WebSocket contract carries the JWT in the `token` query parameter because browsers do not expose arbitrary WebSocket headers through the native constructor. REST uses the required `Authorization: Bearer <JWT>` header.
- JWT uses an HMAC secret from environment configuration. Production deployment must provide a strong secret and rotate it through an operational secret-management process.
- NVML falls back to CPU behavior when no GPU is available. This is useful for development but does not prove the 6 GB GPU admission policy on a CPU-only CI host.
- Ollama models and PaddleOCR assets are local runtime dependencies; a wiped Ollama volume may require model provisioning before model-dependent E2E tests can pass.
- The Compose file emits a warning because its legacy `version` field is obsolete.

## 9. Final SIH 26117 Readiness

**Status: CONDITIONAL / NOT YET READY FOR FINAL SIGN-OFF.**

The architecture contains the required sovereignty, hardware-awareness, deterministic workflow, transactional outbox, project RBAC, and physical failure-injection mechanisms. Clean Docker teardown and rebuild were demonstrated, and the stack boots from fresh volumes. However, the acceptance requirement of a 100% clean test suite was not met: 13 tests failed.

The project should remain in Phase 14 remediation until the failing tests are migrated or the corresponding implementation contracts are corrected, followed by a fresh `docker compose down -v`, `docker compose up --build -d`, and full `pytest` run with zero failures.

## 10. Validation Commands and Evidence

Executed commands:

```powershell
docker compose down -v
docker compose up --build -d
docker compose exec backend python -m pytest -q --tb=no
```

Clean boot evidence included:

```text
Volume project-root_pgdata Created
Volume project-root_ollama_data Created
Container project-root-redis-1 Healthy
Container project-root-db-1 Healthy
Container project-root-worker-1 Started
Container project-root-backend-1 Started
```

Final clean-suite evidence:

```text
.FFFFFsF.....sss..F..FFFFFF............... [100%]
25 passed, 4 skipped, 13 failed, 11 warnings in 117.31s
```

The two most relevant non-fatal warnings are deprecated `pynvml` packaging and an HMAC key shorter than the recommended SHA-256 signing length. These are documented limitations, not silently suppressed failures.

## 11. Pitching to the SIH Judges: The Uniqueness of Our Solution

### True Data Sovereignty

This is not a cloud API wrapper. The model provider is constrained by `validate_local_endpoint`, which permits local and on-premise endpoints such as `ollama`, `localhost`, and approved local domains while rejecting external hosts. The data path therefore remains inside the deployment boundary. JWT identity and project membership are checked for every protected REST operation, and WebSocket access is separately checked against the requested project. A tenant cannot subscribe to another project's event room merely by knowing its UUID.

### Hardware-Awareness

Most hackathon systems assume that model inference fits the machine. This system measures the machine. The NVML resource manager reads free and total VRAM, tracks active inference, estimates model requirements, unloads conflicting models when necessary, and reserves a safety buffer. On a 6 GB target GPU, this changes OOM behavior from a process crash into an admission decision that can be queued or rejected cleanly.

### Deterministic Autonomy

The autonomy layer is a state machine, not an unconstrained `while True` LLM loop. LangGraph explicitly models planning, execution, observation, and reasoning. Plans are Pydantic-validated `ToolCall` objects. Tool execution then adds registry, policy, schema, timeout, result normalization, and audit boundaries. The agent can re-plan after a failed observation, but it is bounded by a maximum step count.

### Resource-Optimized Multimodality

Native documents do not need a vision-language model. DOCX, CSV, and XLSX go through native parsers; OCR is reserved for image-like content; a VLM is reserved for actual visual reasoning. This reduces latency, VRAM pressure, and model churn while preserving a multimodal route for cases that need it.

### Enterprise-grade failure semantics

The transactional outbox separates durable intent from transient delivery. A Redis crash does not erase the PostgreSQL event. Worker leases and recovery make abandoned work visible after a crash. Sandboxes are physically bounded and removed on timeout. These are operational guarantees that ordinary demo applications rarely test against actual stopped containers.

## 12. Codebase Tour for Judges and Evaluators

- `docker-compose.yml`: Defines PostgreSQL/pgvector, Redis, Ollama, backend, and worker topology.
- `backend/app/db.py`: Async SQLAlchemy engine, session factory, and database dependency. `NullPool` prevents cross-event-loop asyncpg reuse.
- `backend/app/events/envelope.py`: Canonical event envelope and derived stream/idempotency keys.
- `backend/app/events/publisher.py`: Writes the audit record and transactional outbox row in one transaction.
- `backend/app/events/dispatcher.py`: Claims pending outbox rows and publishes them to Redis Streams.
- `backend/app/events/consumer.py`: Consumer groups, idempotency keys, visibility timeout, stale-message claiming, and DLQ routing.
- `backend/app/agents/graph.py`: LangGraph state machine and Pydantic plan boundary.
- `backend/app/agents/executor.py`: Registry, policy, schema, timeout, audit, and result boundary around tools.
- `backend/app/models_ai/router.py`: Capability-aware model selection and `/api/v1/ai/chat/stream` SSE route.
- `backend/app/models_ai/resource_manager.py`: NVML telemetry and VRAM admission controller.
- `backend/app/sandbox/runner.py`: Docker isolation, no network, resource limits, file archive transfer, timeout kill, cancellation kill, and output quota.
- `backend/app/security/auth.py`: JWT verification, local endpoint policy, and project membership enforcement.
- `backend/app/tasks/service.py` and `backend/app/tasks/router.py`: Task lifecycle REST contract.
- `backend/worker/main.py`: Redis consumer, task execution, dispatcher, and expired-lease recovery loop.
- `backend/tests/integration/test_failure_modes.py`: Physical Redis outage, worker crash, and sandbox timeout tests.
- `docs/events.md`: WebSocket event parsing contract.
- `docs/openapi.json`: Static REST/OpenAPI contract for consumers and frontend generation.

## 13. UI / Frontend Development Integration Guide

### Authentication

For REST requests, obtain a JWT from the configured identity flow and send it on every protected request:

```http
Authorization: Bearer <JWT>
```

The JWT `sub` must identify a user that has a `ProjectMember` row for the requested project. A valid token without membership returns `403 Forbidden`. Missing or invalid credentials return `401 Unauthorized`.

### Task REST lifecycle

Create a task:

```http
POST /api/v1/projects/{project_id}/tasks
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "task_type": "agentic_workflow",
  "input_payload": {"prompt": "Write and execute a script"}
}
```

The response is `201` with a `TaskResponse` containing `id`, `project_id`, `task_type`, `status`, `input_payload`, optional `result_payload`, `retry_of_task_id`, `created_at`, and `updated_at`. Typical status progression is `QUEUED -> RUNNING -> COMPLETED` or `FAILED`.

Useful lifecycle routes are:

```text
GET  /api/v1/tasks/{id}
GET  /api/v1/projects/{project_id}/tasks
POST /api/v1/tasks/{id}/cancel
POST /api/v1/tasks/{id}/retry
```

The frontend should create the task, subscribe to the project WebSocket, update the task row on `task.started`/running events, and render the final `task.completed` or `task.failed` payload. Polling `GET /api/v1/tasks/{id}` remains the durable fallback.

### WebSocket real-time feed

The endpoint is:

```text
ws://<host>/ws/projects/{project_id}?token=<JWT>
```

The current backend contract validates the JWT from the `token` query parameter for WebSockets. Native browser WebSocket clients cannot reliably set an arbitrary `Authorization` header during construction; REST remains Bearer-header based.

Every pushed event has this JSON shape:

```json
{
  "event_id": "uuid",
  "event_type": "task.started",
  "occurred_at": "2026-09-07T00:00:00Z",
  "source": "task_runner",
  "task_id": "uuid or null",
  "agent_run_id": "uuid or null",
  "correlation_id": "uuid",
  "causation_id": "uuid or null",
  "payload": {"status": "RUNNING"},
  "schema_version": 1
}
```

Clients should parse `event_type` first, use `task_id` as the primary correlation key, and treat `payload` as event-specific. Do not assume that all event types have the same payload fields. The server filters events by resolving the task's project ID before broadcasting.

### SSE chat streaming

The model stream endpoint is:

```text
POST /api/v1/ai/chat/stream
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "model": "auto",
  "prompt": "Explain the result",
  "system": "You are concise"
}
```

The response media type is `text/event-stream`. Each token arrives as an SSE frame:

```text
data: token text

```

A successful stream ends with:

```text
data: [DONE]

```

A provider failure is emitted as:

```text
data: [ERROR] <message>

```

A React client can use `fetch` with `ReadableStream` parsing for POST-based SSE, splitting on double newlines and removing the `data: ` prefix. The frontend should render tokens incrementally and stop on `[DONE]` or surface `[ERROR]` as a failed generation.

### Frontend integration cautions

- Keep project ID and JWT together in the application session context.
- Treat task status as server state; local optimistic state must reconcile with WebSocket events and REST polling.
- Use the event envelope's `schema_version` to prepare for future event evolution.
- Never display a result from a different project merely because a task ID was received; enforce the active project in the client store as a second UI-level guard.
- Do not assume model availability. Use `GET /api/v1/ai/models` to discover registered models and capabilities.
- Keep the current failed legacy tests in mind: the Slice 2 fixture still assumes an unauthenticated API, and should be updated to create an authenticated project context before being used as a frontend contract test.
