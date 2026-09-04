# Backend Architecture Audit — SIH 26117

## Adversarial Red-Team Re-Audit

Audit date: 2026-09-04  
Scope: backend source, deployment files, tests, and exposed API definitions.  
Method: read-only source tracing, targeted repository search, and a focused test run.

The prior audit was treated as a set of hypotheses. Every positive claim was challenged for reachability, executability, dynamic behavior, failure handling, concurrency, constrained hardware behavior, security, frontend consumability, and test evidence.

## 1. Executive Summary

The repository has a recognizable skeleton for a Sovereign On-Premise Agentic AI Workbench: FastAPI routes, PostgreSQL models, Redis Streams, an Ollama provider, a planner/executor/validator vocabulary, filesystem and code tools, a Docker sandbox, document extraction, embeddings, audit logging, WebSockets, and resource sampling.

The red-team conclusion is substantially less favorable than the structural design suggests. The central agent/worker runtime is currently import-broken. `AgentRun` and `PlanStep` are defined in `backend/app/agents/models.py` but imported from `app.tasks.models`; `ToolExecution` is defined in `backend/app/tools/models.py` but also imported from `app.tasks.models`. The focused test run fails during collection on this error, before behavior tests execute. The worker imports `TaskRunner`, which imports the broken orchestrator, so the intended asynchronous agent path cannot start as currently written.

The system therefore structurally resembles the intended workbench, but it is not presently a deployable, genuinely working backend for the claimed architecture. A few primitives are real, especially FastAPI health/API wiring, direct Ollama generation, path containment checks, task persistence/state transitions, and Docker command construction. However, several high-value capabilities are either unreachable, isolated behind mocks, only partially wired, or over-described by their names and comments.

## 2. Final Architecture Verdict

| Capability | Verdict | Red-team conclusion |
|---|---|---|
| Complete architecture | 🔴 Missing | Major runtime and deployment gaps remain. |
| Genuinely agentic | 🟡 Partial | An LLM planner and bounded plan loop exist, but the runtime import path is broken and there is no action-observation replanning loop. |
| Genuinely local-first | 🟡 Partial | Ollama and local PostgreSQL/Redis are intended, but deployment is incomplete and external-egress proof is insufficient. |
| Model routing | 🟡 Partial | Environment-variable tier lookup works; capability/load/VRAM routing does not. |
| Manual model selection | 🔴 Missing | Chat accepts a tier, not an explicit model identifier or model list. Tasks always select tier 1. |
| Dynamic LLM-driven planning | 🟡 Partial | Planner calls Ollama for JSON steps, but tool availability, state, and observations are not supplied as a controlled runtime contract. |
| Multi-step execution | 🟡 Partial | A hard-coded six-step cap and one retry exist, but execution is sequential, the worker path is broken, and step results are not fed into the next planning decision. |
| Tools | 🟡 Partial | Tool classes and schemas exist; registration and executor signatures prevent several tools from working through the normal path. |
| Sandboxed execution | 🟡 Partial | Docker flags request useful isolation, but the image/build/deployment path is incomplete and resource/output controls are limited. |
| Document analysis | 🟡 Partial | PDF/image rasterization and Ollama vision calls exist, but indexing, ownership, file validation, and runtime tests are weak. |
| Image/multimodal analysis | 🟡 Partial | Images are sent to Ollama, but the configured tier-2 default is not guaranteed to be a vision model. |
| Event-driven task execution | 🔴 Weak / Risky | Redis Streams and a worker consumer exist in source, but compose does not define the worker, imports fail, and DB-to-Redis publishing is not recoverable. |
| GPU/VRAM optimization | 🔴 Missing | Only optional GPU utilization sampling exists; no VRAM accounting, admission control, model unloading, or actual GPU deployment configuration is active. |
| Frontend readiness | 🟠 Weak / Risky | Basic task polling and a WebSocket shape exist, but chat streaming, model selection, authorization, upload limits, cancellation, and reliable status delivery are incomplete. |
| Architectural refactoring need | 🟢 Confirmed | Import ownership, deployment topology, event delivery, authorization, model/provider contracts, and tool registration need architectural correction. |

## 3. Current Project Structure

```text
backend/
  app/
    main.py                  FastAPI application and lifespan tasks
    db.py                    Async SQLAlchemy engine/session/base
    agents/                  Planner, orchestrator, executor, validator, agent models
    common/                  Shared exceptions
    events/                  Event envelope, catalog, persistence, Redis publisher/consumer
    models_ai/               Provider interface, Ollama provider, tier lookup, chat route
    monitoring/              CPU/RAM/GPU percentage sampler and metrics route
    realtime/                In-memory WebSocket manager and Redis event tailer
    sandbox/                 Docker subprocess runner
    security/                Shared-token authentication and audit logging
    tasks/                   Task models, repository, service, routes, worker runner
    tools/                   Tool base/registry, policy, filesystem, code, document tools
    workspace/               Project path boundary, uploads, embeddings, document chunks
  tests/                     Unit, integration, and nominal E2E tests
  worker/main.py             Redis Stream worker process
  alembic/                   Database migrations

docker-compose.yml           PostgreSQL/pgvector, Redis, Ollama, backend services
Docker/sandbox-base.Dockerfile  Minimal non-root sandbox image
Makefile                     Compose, migration, seed, test, and OpenAPI commands
docs/                        OpenAPI and event documentation
workspace_data/              Project workspace data
```

The module boundaries are sensible on paper. The principal weakness is not absence of directories but inconsistent ownership: agent entities and tool execution entities are defined in one package and imported from another, while deployment configuration does not include every process required by the source architecture.

## 4. Actual Technology Stack

- Backend framework: FastAPI with Uvicorn.
- Runtime: Python 3.11 is targeted by the sandbox image; the local verification environment used Python 3.14.
- API architecture: REST-style FastAPI routes under `/api/v1`, a health route, and a WebSocket route.
- Async model: `async def`, SQLAlchemy async sessions, `httpx.AsyncClient`, Redis asyncio client, subprocesses through asyncio. File upload copying and some filesystem operations remain synchronous inside async handlers.
- LLM integration: direct HTTP calls to Ollama `/api/generate` and `/api/embeddings`.
- Model serving: Ollama is declared in Compose. No vLLM, Hugging Face runtime, or model lifecycle manager is implemented.
- Agent architecture: planner, orchestrator, executor, validator, SQL persistence models.
- Routing: deterministic environment-variable tier names only.
- Queue/event system: Redis Streams, consumer groups, acknowledgements, pending-message reaping, and a nominal DLQ.
- Persistence: PostgreSQL through SQLAlchemy async and Alembic; pgvector `Vector(768)` document chunks.
- Document processing: pypdfium2 PDF rasterization and base64 image submission to Ollama; fixed-size text chunking and embeddings.
- Multimodal processing: Ollama `images` payload, conditional on a compatible model being configured.
- Sandbox: Docker subprocess with no network, read-only root, CPU/memory/PID limits, and temporary bind mounts.
- Testing: pytest/pytest-asyncio, unit tests, mock-heavy E2E tests, and external-service-dependent tests.
- Configuration: environment variables plus hard-coded localhost fallbacks. The Compose file references a missing `backend/Dockerfile` and has the NVIDIA reservation commented out.

## 5. Actual Request Execution Flow

### Direct chat

```text
Authenticated HTTP POST /api/v1/ai/chat
        |
        v
ChatRequest validation (prompt, optional system/options, integer tier)
        |
        v
TierRouter.get_model_for_tier(tier)
        |
        v
New OllamaProvider -> POST /api/generate with stream=false
        |
        v
ChatResponse(model, response)
```

This path bypasses the task queue and agent runtime. It supports tier selection but not explicit model selection or user-facing streaming.

### Intended task path, as traced in source

```text
Authenticated POST /api/v1/projects/{project_id}/tasks
        |
        v
TaskService creates CREATED task, persists event, changes to QUEUED,
then persists another event and attempts Redis XADD
        |
        v
Redis stream:task -> worker StreamConsumer -> TaskRunner
        |
        +--> direct task: hard-coded tier 1 Ollama generate
        |
        +--> agentic_workflow: AgentOrchestrator
                    -> Planner Ollama structured JSON
                    -> sequential PlanStep creation
                    -> PolicyEngine
                    -> Tool.run with timeout
                    -> Validator
                    -> at most one retry / six total steps
```

The flow is not operational end to end today: the worker import fails, Compose does not define a worker service, and the executor's import and tool-call contracts contain additional runtime failures.

## 6. Local LLM Architecture

`ModelProvider` is an abstract-looking interface, but its methods are empty abstract methods and the runtime directly constructs `OllamaProvider` in the chat route, planner, task runner, document tools, and embedding service. There is no registry of loaded models, lifecycle manager, model health state, provider fallback, unload policy, or capacity reservation.

Ollama generation uses a new `httpx.AsyncClient` per request and a fixed timeout. Normal generation sets `stream: false`. The provider has a stream generator, but no route consumes it. Structured generation asks Ollama for JSON and `format: json`, then parses JSON; it does not validate the returned object against the declared Pydantic schema before the planner constructs step models.

Image payloads are supported by the provider, but model compatibility is configuration-dependent. The default tier-2 model is `llama3.1:70b`, which is not a safe assumption for vision support or a 6 GB RTX 4050. Failures become HTTP 502 in direct chat or task failure in the runner; no provider fallback or model retry strategy is present.

## 7. Model Routing

Routing is hard-coded by tier names read from environment variables:

- tier 0 defaults to `llama3.1`;
- tier 1 defaults to `mixtral`;
- tier 2 defaults to `llama3.1:70b`;
- embedding defaults to `nomic-embed-text`.

This is rule-based name selection, not capability-based, LLM-assisted, load-aware, or hybrid routing. There is no inspection of installed models, context length, quantization, GPU memory, current load, task cost, or fallback capacity. The planner always uses tier 1. The document extractor always uses tier 2. The ordinary task runner always uses tier 1. The query tool hard-codes the embedding model instead of using `TierRouter.get_embedding_model()`.

## 8. Custom Model Chat

The backend does not expose an explicit `model` field, model registry endpoint, or validated model allow-list. The frontend can expose `Auto` only indirectly by choosing a tier if it reproduces the current convention; it cannot reliably offer `Model A`, `Model B`, and `Model C` using the existing chat contract. Implementing explicit selection would require an API and policy contract, not merely a frontend dropdown.

## 9. Agent Architecture

Agent definition is implicit in the planner prompt and tool registry rather than a persisted agent configuration or capability document. Agent state is represented by `AgentRun`, `PlanStep`, and `ToolExecution` database records, but imports are wrong and the model fields do not match the orchestrator's construction: `PlanStep` defines `step_index` and `args`, while the orchestrator uses `step_number` and `tool_args`; `AgentRun.tier_used` is non-null but is not supplied.

The runtime classes are conceptually separated into planner, executor, validator, and orchestrator. The actual lifecycle is therefore a useful design intent but is not currently executable without correcting the model contract and imports.

## 10. Dynamic Planning & Reasoning

There is a genuine LLM call in `Planner.plan`, and it can return a list of tool steps from a JSON schema. The orchestrator can call the planner again after validation failure, passing a textual failure reason. This survives as a limited dynamic planning claim.

It does not implement a complete observe-and-reason loop. The planner receives the original objective and, on retry, one failure string. It is not given a controlled tool catalog, current workspace state, prior tool outputs, structured observations, model-selected next action, or explicit termination decision. The normal code executes every returned draft step sequentially. Thus the actual system is closer to `LLM creates a batch plan -> hard-coded executor runs it -> validator may request one new batch` than to a continuously reasoning agent.

## 11. Multi-Step Agent Execution

Step persistence and a six-step total cap are present in source. One validation retry is present. Tool calls are wrapped in `asyncio.wait_for` using each tool's declared timeout.

Important limitations are decisive:

- The agent runtime cannot import as written.
- Execution is sequential and holds one session through the workflow.
- Tool results are stored but are not supplied as observations to the next planner call.
- `retryable` is declared but never used.
- There is no per-step retry policy, backoff, compensation, or resumable checkpoint.
- Cancellation is checked only at the start of an outer loop, not during a running LLM call or tool.
- The validation fallback passes general tasks without proving a task-specific outcome.
- There is no robust loop-detection or persisted lease for an agent run.

## 12. Tool System

Registered classes include filesystem read/write/list, code execution, test execution, document extraction, and document query. Pydantic input schemas and a deterministic policy interception point are good foundations.

The normal policy module imports filesystem tools for registration, but does not import code or document tool modules. Unless another import side effect occurs first, those tools are absent from `TOOL_REGISTRY` and are denied as unregistered. More seriously, `Executor` always calls `tool.run(..., db=self.db)`, while filesystem tool signatures do not accept `db`; a real filesystem step therefore fails with `TypeError` even when policy allows it. `ToolExecution` is imported from the wrong module. These are runtime contract failures, not cosmetic issues.

The planner is not constrained by a runtime-generated tool catalog, and tool arguments are validated only after a model has selected a tool. Results are converted to strings and can be emitted in event payloads without output-size limits or redaction.

## 13. Sandbox Security

The sandbox requests meaningful controls: `--network=none`, `--memory=256m`, `--cpus=0.5`, `--pids-limit=64`, `--read-only`, a temporary filesystem, a read-only workspace mount, a writable scratch mount, and a non-root user in the base image. The subprocess has a timeout and attempts `docker rm -f` on timeout.

Operational and security gaps remain:

- Compose does not build or run the sandbox image, and the referenced backend image Dockerfile is missing.
- The host Docker daemon is controlled by the backend process. A Docker daemon/socket boundary is not shown; compromise of the backend/container environment could have host-level consequences depending on deployment.
- The command and filenames are model-controlled. There is no allow-list for executable commands, filename normalization before writing, output quota, disk quota, or input size quota.
- `TemporaryDirectory` cleanup is useful, but cleanup behavior after daemon failure is not verified.
- Timeout cancellation may leave subprocess/daemon work in ambiguous states if Docker itself hangs.
- The base image installs only pytest and has no explicit seccomp/AppArmor profile or dropped capability list in the runner command.

The controls are credible as a starting point, but they do not establish a complete security boundary against malicious or incorrect LLM-generated code.

## 14. Document & Multimodal Capabilities

PDFs are rasterized up to 20 pages; non-PDF files are read as raw bytes and submitted as base64 images. The upload endpoint accepts only PNG, JPEG, and PDF content types. There is no DOCX parser, spreadsheet parser, CSV/JSON-specific ingestion, OCR engine such as PaddleOCR, or content-sniffing validation. The implementation's “document” path is primarily image/PDF-to-VLM extraction.

The extractor calls a tier-2 model and then embeds extracted text. The default tier-2 model is not guaranteed to be multimodal. The embedding path uses fixed-size character slicing, sequential embedding calls, a hard-coded model, and a fixed 768-dimension database column. Query uses pgvector cosine distance and top three chunks, then a tier-1 synthesis call. It filters by file ID but does not establish that the file belongs to the caller's project.

The nominal VLM E2E test catches all exceptions and calls `pytest.skip`, so unavailable models, service failures, and functional failures can all avoid a failing test.

## 15. Event-Driven Task Queue

Redis Streams, consumer groups, acknowledgements, stale pending-message claiming, idempotency keys, and a DLQ function exist in source. The worker filters for `task.queued` events and invokes `TaskRunner`.

The architecture is not a reliable operational queue today. `docker-compose.yml` defines no worker service, the worker defaults to `localhost` for Redis, the API task dependency also hard-codes `localhost` rather than using `REDIS_URL`, and the worker import chain fails. The publisher commits the PostgreSQL event before Redis `XADD`; if Redis fails, a durable database record exists without a recoverable stream delivery. This is not an outbox or two-phase commit.

Consumer failure handling also has gaps. Handler failure deletes the idempotency key while leaving the message pending; malformed envelope processing is caught by the broad loop rather than routed consistently to a DLQ; retry accounting is tied to the stale-message reaper; and shutdown does not explicitly await the reaper task.

## 16. GPU / VRAM Optimization

The only implemented hardware logic is optional NVML GPU percentage sampling plus CPU/RAM sampling. No VRAM metric is captured. No model admission control, quantization selection, concurrency limit, model unloading, GPU lock, batching, memory watermark, or fallback-to-CPU policy is implemented.

The Compose NVIDIA configuration is commented out. The default tier-2 70B model is incompatible with the stated approximately 6 GB RTX 4050 target unless a separate, undocumented configuration changes the model and serving behavior. The 20-page PDF cap is a workload cap, not VRAM management.

## 17. Performance & Latency

Major latency sources are model load/warm-up, sequential PDF page rendering, one embedding HTTP request per fixed chunk, multiple LLM calls per agent run, and synchronous filesystem/upload work inside async request handlers. Each Ollama operation creates a fresh HTTP client. Normal chat and task responses wait for full generation; the stream method is unused.

Concurrency is not governed around Ollama or GPU access. Multiple workers/tasks could independently invoke large models and exhaust VRAM. Queue delays are possible when a worker exists, but no worker concurrency or priority policy is configured. There is no cancellation propagation into `httpx` generation or sandbox work beyond the local timeout scope.

## 18. Edge Cases & Failure Handling

Handled or partly handled cases include invalid tier values, provider exceptions in direct chat, task status transition checks, missing parent tasks, path traversal, tool argument Pydantic validation, tool timeout, Docker command timeout, Redis consumer reconnect loops, and optional NVML failure.

High-risk unhandled or weakly handled cases include worker import failure, missing Docker build context, Redis/DB event divergence, unavailable model or wrong model modality, malformed structured JSON, vector dimension mismatch, oversized uploads, invalid or hostile filenames, file/project ownership violations, cancellation during active work, duplicate task execution after leases, partial agent persistence, and database failure while publishing events. Generic exceptions frequently become strings exposed to clients or persisted without classification.

## 19. Security & Sovereignty

The system uses local service names and local persistence by intent. The direct provider sends prompts, images, and system prompts to the configured Ollama URL. No deliberate external API integration is visible in the inspected path.

Sovereignty is not sufficient by intent alone. `OLLAMA_BASE_URL` is environment-controlled, and there is no allow-list preventing an external endpoint. The integration test named for egress uses mocking/interception rather than proving production network behavior. The Docker sandbox has no network, but the backend and Ollama services do not have equivalent egress restrictions in Compose.

Authentication is a single shared bearer token with a demo default. There is no user identity, project membership, RBAC enforcement, or ownership check on task and file routes. Any authenticated holder can potentially access arbitrary project/task IDs. WebSocket authentication accepts the shared secret in a query parameter and does not authorize project membership. Document query lacks project/file ownership validation. These are direct violations of strong tenant and sovereignty claims.

## 20. Frontend Readiness

- Chat: basic synchronous chat is consumable with bearer authentication and a tier integer.
- Streaming: not consumable; the provider generator has no HTTP streaming response or WebSocket model-stream integration.
- Model selection: no explicit model list or model identifier contract.
- Agent selection: task type can be submitted, but no agent catalog or validated capability contract exists.
- Agent execution: intended task endpoint exists, but the worker/orchestrator path is broken.
- Task status: create, get, list, cancel, and retry routes exist.
- File upload: a basic route exists, with MIME allow-list but no size/content checks.
- Document analysis: exists as a tool, not as a clear frontend workflow endpoint.
- Image analysis: exists indirectly through extraction and depends on a vision-capable model.
- Progress updates: WebSocket/event source exists structurally, but it misses pre-start events and has authorization and deployment issues.
- Errors: HTTP and task error fields exist, but error classes and retry semantics are inconsistent.
- Cancellation: endpoint marks cancellation/requested state; active work is not interrupted.

A demo frontend could call health, synchronous chat, task CRUD, and upload with assumptions. The planned feature-complete frontend cannot be implemented cleanly without backend refactoring and contract completion.

## 21. API Inventory

| Endpoint | Purpose | Assessment |
|---|---|---|
| `GET /health` | Health response | Implemented but does not verify DB, Redis, Ollama, or worker health. |
| `POST /api/v1/ai/chat` | Synchronous Ollama chat | Runtime path exists; tier-based only and non-streaming. |
| `POST /api/v1/projects/{project_id}/tasks` | Create and enqueue task | Emits events and returns task; delivery/deployment concerns. |
| `GET /api/v1/tasks/{id}` | Retrieve task | No ownership authorization. |
| `GET /api/v1/projects/{project_id}/tasks` | List project tasks | No project membership authorization. |
| `POST /api/v1/tasks/{id}/cancel` | Request cancellation | Advisory for running work. |
| `POST /api/v1/tasks/{id}/retry` | Create retry task | Creates a new task from terminal states. |
| `POST /api/v1/projects/{project_id}/files` | Upload PNG/JPEG/PDF | Basic write path; unbounded and weakly validated. |
| `GET /api/v1/metrics/latest` | Latest resource metrics | Sampling is observability only, not scheduling. |
| `WS /ws/projects/{project_id}` | Project event feed | Query-token auth, no membership authorization, startup cursor misses old events. |

## 22. Testing & Reliability

The focused command `venv\Scripts\python.exe -m pytest -q backend\tests\unit backend\tests\e2e --disable-warnings --maxfail=1` failed during collection with `ImportError: cannot import name 'AgentRun' from 'app.tasks.models'`. Therefore the agent tests do not currently provide executable confidence.

The nominal E2E tests are mock-heavy: planner, validator, executor, database, and Redis are commonly mocked. The document/VLM test skips on any exception, including service absence and functional failure. The sandbox test depends on a pre-existing Docker image. Tests do not cover worker startup, Compose topology, project isolation, explicit model selection, stream delivery durability, tool registration, executor signature compatibility, upload limits, WebSocket authorization, cancellation interruption, VRAM behavior, or concurrent model calls.

## 23. Strong Architectural Decisions

- Local Ollama, PostgreSQL/pgvector, Redis, and Docker are appropriate technology choices for an on-premise direction.
- FastAPI and async database/HTTP/Redis APIs provide a reasonable foundation for I/O-heavy work.
- A separate worker process and Redis Stream consumer are appropriate concepts for expensive tasks.
- Pydantic request/tool schemas and a policy interception point establish useful validation boundaries.
- Resolved workspace paths with strict containment checks address ordinary `..` traversal and absolute-path injection.
- The sandbox requests several meaningful container constraints.
- Task state transitions, retry-as-new-task, audit events, and event envelopes show awareness of operational concerns.
- Agent planner, executor, and validator separation is a good direction even though the contracts are currently inconsistent.

## 24. Architectural Weaknesses

- Core model imports and field names are inconsistent, preventing agent runtime startup.
- Deployment topology omits the worker and references a missing backend Dockerfile.
- Event persistence and queue publication are split by a non-recoverable commit boundary.
- Routing is merely environment-variable lookup and cannot manage constrained hardware.
- Provider abstraction is bypassed by direct Ollama construction throughout the code.
- Tool registration depends on import side effects and is incomplete.
- Executor/tool signatures do not share one interface.
- Authentication has no authorization or tenant isolation.
- Streaming and cancellation are declared by adjacent primitives but absent from user workflows.
- Tests simulate central behavior rather than proving production integration.

## 25. Top 10 Risks

| Risk | Location | Evidence | Impact | Severity | Recommended Direction |
|---|---|---|---|---|---|
| 1. Agent/worker cannot import | `backend/app/agents/orchestrator.py`, `executor.py`, `validator.py` | Models imported from wrong packages; focused pytest collection fails | No agentic task execution | Critical | Establish one model ownership package, correct imports/fields, and add startup/import tests. |
| 2. Deployment cannot run claimed topology | `docker-compose.yml` | Missing `backend/Dockerfile`; no worker service; GPU section commented | Demo and production startup fail or omit workers | Critical | Define reproducible backend and worker images/services and health dependencies. |
| 3. Cross-project data access | `security/auth.py`, task/file routes, document query | Shared token; no membership/file ownership checks | Confidentiality breach | Critical | Add identity, project authorization, object-level checks, and isolation tests. |
| 4. Event loss after DB commit | `events/publisher.py` | PostgreSQL commit precedes Redis XADD | Tasks remain queued with no worker delivery | Critical | Use transactional outbox and recoverable dispatcher, or a proven queue transaction strategy. |
| 5. Tool path fails in real executor | `agents/executor.py`, `tools/filesystem_tools.py` | Executor passes `db`; filesystem signatures reject it | Basic agent file workflows fail | High | Define and type one Tool protocol; integration-test every registered tool. |
| 6. Model routing is unsafe for hardware | `models_ai/tier_router.py`, Compose | Default 70B tier; no VRAM/load control | OOM, latency collapse, unavailable models | High | Inventory models, estimate memory, serialize/admit GPU work, and configure actual GPU runtime. |
| 7. False confidence from tests | `backend/tests/e2e/*` | Core collaborators mocked; VLM failures skipped | Broken runtime reaches evaluation | High | Add real service integration tests and fail on unexpected capability absence. |
| 8. Active work cannot be cancelled | `tasks/service.py`, `agents/orchestrator.py`, runner | Cancellation is advisory and not consumed by worker/tool | Resource waste and stale state | High | Propagate cancellation tokens, kill subprocesses, cancel HTTP requests, and persist leases. |
| 9. Sandbox boundary is incomplete | `sandbox/runner.py`, Docker setup | Docker daemon dependency; no quotas/output caps; incomplete image path | Code execution escape/resource risk | High | Harden daemon boundary, capabilities/seccomp, quotas, command policy, and cleanup tests. |
| 10. No frontend streaming/model contract | `models_ai/router.py`, provider, realtime | `stream` unused; no model ID/list endpoint | Planned UX cannot be built against stable API | Medium | Define chat stream protocol, model catalog, agent/task event schema, and cancellation contract. |

## 26. SIH 26117 Compliance Matrix

| Requirement | Status | Evidence | Gap | Severity |
|---|---|---|---|---|
| On-premise/local LLM inference | 🟡 Partial | Ollama service and local provider | No enforced local endpoint or active GPU deployment guarantee | High |
| Sovereign data handling | 🟠 Weak / Risky | Local DB/workspace intent | External URL not blocked; no tenant isolation; egress test is mocked | Critical |
| Agentic planning | 🟡 Partial | Planner calls Ollama for structured steps | Worker broken; limited plan/retry loop; no rich observations | Critical |
| Multi-step workflows | 🟡 Partial | Orchestrator and six-step cap | Runtime model contract broken; no resumable execution | Critical |
| Model routing | 🟡 Partial | TierRouter environment mapping | No capability, load, VRAM, or fallback routing | High |
| Manual model selection | 🔴 Missing | Chat request has tier only | No explicit model contract/catalog | Medium |
| Tool integration | 🟡 Partial | Tool classes, schemas, policy | Registration/signature/runtime failures | Critical |
| Secure code execution | 🟡 Partial | Docker restrictions | Missing deployment/hardening/quotas and host-daemon risk | High |
| Document understanding | 🟡 Partial | PDF/image extraction and embeddings | No broad formats, ownership checks, or reliable test | High |
| Multimodal/vision | 🟡 Partial | Ollama images payload | Tier default may not support vision; test skips failures | High |
| Event-driven execution | 🔴 Weak / Risky | Redis Streams and consumer code | No worker Compose service; import and outbox failures | Critical |
| GPU/VRAM optimization | 🔴 Missing | Optional GPU percentage sampler | No VRAM control or scheduling | High |
| Progress/streaming | 🟡 Partial | WebSocket and event publisher | No LLM stream; missed events; weak auth | High |
| Security/authentication | 🟡 Partial | Bearer token and audit calls | Shared demo secret; no authorization/RBAC | Critical |
| Reliability/recovery | 🟠 Weak / Risky | Retry route and stream reaper | No durable delivery, active cancellation, or integration proof | Critical |
| Frontend integration | 🟡 Partial | REST task/file/chat routes | Planned UI contracts are incomplete and runtime worker is broken | High |

## 27. Architecture Scorecard

| Area | Score / 10 | Reason |
|---|---:|---|
| Architecture | 3 | Clear intended layers, broken central runtime. |
| Modularity | 5 | Useful directories and responsibilities, inconsistent contracts. |
| Local LLM support | 4 | Direct Ollama path works conceptually, no lifecycle/health/fallback. |
| Model routing | 2 | Tier name lookup only. |
| Agent orchestration | 2 | Strong skeleton, import and persistence mismatches. |
| Dynamic planning | 4 | Real structured planner call, shallow observation loop. |
| Tool architecture | 3 | Schemas/policy/registry present, runtime registration/signature gaps. |
| Sandbox | 4 | Good requested flags, incomplete operational boundary. |
| Multimodal | 3 | Image/PDF-to-Ollama path, modality and test weaknesses. |
| Queueing | 2 | Redis mechanics present, deployability and delivery reliability fail. |
| GPU optimization | 1 | Utilization sampling only. |
| Performance | 3 | Async primitives but sequential, repeated clients, uncontrolled concurrency. |
| Reliability | 2 | Some retries/state handling, central path cannot start. |
| Security | 3 | Path checks and token comparison, no authorization/tenant isolation. |
| Frontend readiness | 3 | Basic CRUD/chat shape, missing core UX contracts. |
| Extensibility | 4 | Provider/tool abstractions exist but are bypassed or side-effect based. |
| Observability | 4 | Audit/events/metrics exist, health and delivery visibility incomplete. |
| Testing | 2 | Collection failure and mock-heavy/skipping evidence. |
| SIH alignment | 3 | Strong conceptual alignment, weak verified implementation. |

**Revised overall architecture score: 3.0 / 10.** This is a maturity score for the current repository, not a score for the intended design.

## 28. CRITICAL FINAL CONCLUSIONS

### What is genuinely implemented?

A FastAPI application can expose health and direct chat routes. The direct chat path selects a configured tier name and calls Ollama synchronously. PostgreSQL/SQLAlchemy task persistence, basic task state transitions, retry task creation, path containment, bearer-token authentication, audit/event object construction, Redis Stream primitives, Docker command construction, PDF rasterization, base64 image submission, pgvector query construction, and optional GPU percentage sampling are real source-level implementations.

### What is only structurally present?

The complete agent worker pipeline, model registry/lifecycle, capability-aware router, frontend streaming, reliable event bus, GPU/VRAM scheduler, broad document-analysis system, tenant security model, and production sandbox boundary are primarily structural. Their names and modules exist, but the runtime path is broken or incomplete.

### What is partially implemented?

LLM planning, bounded multi-step execution, retry feedback, filesystem tools, code sandboxing, document/VLM extraction, embeddings/RAG, task queueing, WebSocket progress, cancellation, and local-first deployment all have meaningful pieces. None currently satisfies the full capability implied by the architecture diagram.

### What is missing?

Explicit model selection/catalog, real streaming, project authorization, reliable DB-to-queue delivery, worker deployment, VRAM-aware scheduling, model lifecycle management, robust cancellation, broad document formats, strict structured-output validation, complete tool registration, and production-grade integration tests are missing.

### What is architecturally risky?

The highest risks are the import-broken worker, missing deployment service/image, cross-project access, non-atomic event publishing, inconsistent ORM/tool contracts, uncontrolled large-model concurrency, advisory cancellation, and over-trust in mock/skip-heavy tests. These risks can cause either complete feature failure or serious confidentiality/resource incidents.

### What would a technical evaluator likely challenge?

They would likely challenge whether the worker can start, whether the claimed agentic path is executable, whether model routing does anything beyond string lookup, how a 6 GB GPU is protected from a 70B default, whether tools really run through the executor, how event loss is recovered, whether users can access one another's projects, whether streaming exists, and whether the E2E tests prove production behavior.

### What would a technical evaluator likely praise?

They would likely praise the coherent local-service direction, the separation of planner/executor/validator concepts, the use of typed tool inputs, path containment, several Docker sandbox restrictions, Redis Stream/consumer-group intent, task lifecycle modeling, audit/event vocabulary, and the decision to use local pgvector/Ollama primitives rather than an obviously cloud-dependent architecture.

### Can the current backend support the intended frontend?

Only a limited demo frontend. It can support health checks, synchronous chat, basic task polling, and basic file upload after assuming the environment is manually repaired. The intended workbench UI, with selectable models, streaming chat, trustworthy agent execution, progress, document/image workflows, authorization, and cancellation, cannot be supported without backend changes.

### Does the backend require architectural refactoring?

Yes. The categories should remain separate:

- **Critical Architectural Changes:** correct model ownership/imports and ORM field contracts; define and deploy the worker; replace DB-then-Redis publication with an outbox/recoverable dispatcher; establish identity and project authorization; define a real provider/model/tool contract.
- **Feature Enhancements:** explicit model catalog and selection; streaming protocol; agent catalog; structured observations; broader document formats; frontend task/event contracts.
- **Performance Optimizations:** persistent HTTP clients; batching; concurrency/admission control; model warm-up/unload strategy; chunking improvements; bounded output and upload processing.
- **Security Improvements:** local endpoint allow-list; upload size/content validation; filename hardening; sandbox capability/seccomp/daemon hardening; WebSocket authorization; output redaction and quotas.
- **Normal Bug Fixes:** import paths, `PlanStep` field names, missing `tier_used`, tool `db` signature mismatch, tool registration imports, Redis URL configuration, and resource-sampler/provider cleanup.

## Claims That Survived Verification

1. Local Ollama HTTP generation is represented by a concrete provider and direct chat call.
2. Filesystem path containment resolves traversal and rejects absolute paths in ordinary cases.
3. Docker sandbox flags request network, CPU, memory, PID, and filesystem restrictions.
4. Redis Stream consumer-group mechanics, acknowledgements, and stale-message handling are present.
5. Basic task state and retry concepts are implemented.
6. An LLM-backed structured planner call exists in source.
7. Optional NVML GPU utilization sampling exists.

These survived only as bounded claims about source-level primitives, not as proof of complete production capabilities.

## Claims That Were Overstated

- “Model routing” was overstated: it is tier-to-environment-string mapping.
- “Agentic execution” was overstated: the central worker path does not import and the loop is batch-plan plus validation retry.
- “Tool integration” was overstated: registration and executor signatures prevent normal execution of important tools.
- “Sandbox security” was overstated: useful flags exist, but deployment and host-daemon boundaries are incomplete.
- “Event-driven execution” was overstated: there is no worker service in Compose and event publication can lose delivery.
- “GPU optimization” was overstated: percentage sampling is not VRAM optimization.
- “Streaming” was overstated: only an unused provider generator exists.
- “Multimodal document analysis” was overstated: it depends on a compatible model and tests can skip all failures.
- “Frontend readiness” was overstated: core model, stream, authorization, cancellation, and agent contracts are absent.

## Previously Missed Problems

1. The agent models are imported from the wrong package and have field mismatches with their callers.
2. `ToolExecution` is imported from the wrong package.
3. The Compose file references a missing backend Dockerfile and does not run a worker.
4. Normal tool registration imports filesystem tools but not code/document tools.
5. The executor passes `db` to filesystem tools that reject that keyword.
6. Task and Redis dependencies hard-code localhost, conflicting with container networking.
7. Upload size, content sniffing, and filename hardening are absent.
8. WebSocket auth uses a query secret and does not authorize project membership.
9. Realtime starts at `$` and intentionally misses events emitted before API startup.
10. The query tool bypasses configured embedding-model selection and assumes 768 dimensions.

## New Critical Risks

The newly decisive risk is that the central claimed feature cannot pass import-time startup. This means prior behavior tests that mock the central collaborators cannot establish runtime readiness. The second is the combined deployment risk: even after import repair, the Compose topology omits the worker and references a missing image build file. Together these move the verdict from “partially implemented backend” to “architectural prototype with a limited direct-chat path and several unverified subsystems.”

## Features That Are Only Structurally Present

- Complete asynchronous worker execution.
- Reliable event-driven task delivery.
- Agent persistence lifecycle.
- Capability-aware multi-model routing.
- Model lifecycle and VRAM management.
- User-facing LLM streaming.
- Secure multi-tenant workspaces.
- Fully registered all-tool catalog.
- Production-grade multimodal ingestion.
- End-to-end cancellation and recovery.
- Frontend-ready progress/error contracts.

## Features That Are Genuinely Runtime-Implemented

- FastAPI application and health route.
- Direct synchronous Ollama generation path, subject to configured Ollama availability.
- Tier integer validation and environment-based model name lookup.
- Basic SQLAlchemy task/project persistence code.
- Basic path containment and project-directory creation.
- Bearer-token comparison and rejection of invalid credentials.
- Source-level Redis event and consumer primitives.
- Source-level Docker sandbox invocation with timeout handling.
- Source-level PDF rasterization/image payload construction.
- Optional CPU/RAM/GPU utilization sampling.

## Revised SIH 26117 Compliance Score

**3.0 / 10.** The repository aligns with SIH 26117 in vocabulary, local components, and intended topology, but the most important evaluator-visible properties are not verified and several are blocked by concrete runtime/deployment defects.

## Revised Overall Architecture Score

**3.0 / 10.** The design direction is credible; the current executable system is not yet a reliable Sovereign On-Premise Agentic AI Workbench backend.

## 29. FINAL ONE-PAGE VERDICT

This backend structurally resembles a Sovereign On-Premise Agentic AI Workbench, but it is not genuinely that backend in its current repository state. The direct chat path and several supporting primitives are real. The agentic task path, however, fails at import time because the orchestrator, executor, and validator import persistence models from the wrong modules and use fields that do not match those models. The deployment definition further omits the worker and references a missing backend Dockerfile.

The strongest implemented ideas are local Ollama/PostgreSQL/Redis choices, typed tools, path boundaries, Docker restrictions, task state modeling, and a planner/executor/validator decomposition. The most serious challenges are runtime reachability, event durability, tenant authorization, tool contract consistency, VRAM safety, cancellation, and weak integration evidence.

An experienced SIH evaluator would likely classify this as an architecture prototype or partially implemented backend, not a complete sovereign agentic workbench. It can become the intended system, but only after critical architectural changes are made and demonstrated with real service-backed tests. The report's central red-team conclusion is therefore: **the repository only structurally resembles the intended SIH 26117 backend today; it does not yet provide a verified, deployable, secure, genuinely agentic implementation.**

**Audit performed in read-only mode. The only repository write permitted during this audit was the creation of this `Report.md` file. No source code, configuration, tests, dependencies, or other project files were modified.**
