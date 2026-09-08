# PS26117 — Phase 15 Master Development Prompt
## Sovereign On-Premise Agentic AI Workbench for MRPL
### Enterprise Stabilization · Sovereign Runtime Verification · Deep Agentic Integration · Hardware-Aware Multi-Model Execution · Production-Grade Fault Tolerance · Real-Time Observability · Demonstrable Data Sovereignty

**Project:** Sovereign On-Premise Agentic AI Workbench (PS26117)
**Competition:** Smart India Hackathon 2026
**Sponsor Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL)
**Theme:** Smart Automation
**Document Purpose:** This is a master development prompt meant to be handed directly to an AI coding agent (or read as an engineering brief by the human team) to drive Phase 15 implementation work. It is written as an instruction set, not a tutorial — every section states what must exist, why it matters to the problem statement, and the concrete contracts the implementation must satisfy.

---


## TABLE OF CONTENTS

1. How to Use This Document
2. Your Role
3. Executive Mandate (Five Principles)
4. Engineering Philosophy — The Standing Filter
5. Primary System Architecture
6. Section One — Sovereignty and Local Execution Verification
7. Section Two — Local Multi-Model Runtime
8. Section Three — Agentic Orchestration Core
9. Section Four — Multimodal Document and Knowledge Processing
10. Section Five — Tool Execution and Sandboxing
11. Section Six — Artifact Management and Real Deliverables
12. Section Seven — Workflow Orchestration and Canvas Compatibility
13. Section Eight — Real-Time Frontend-Backend Contracts
14. Section Nine — Workspace and File System Management
15. Section Ten — Real-Time Terminal and Sandbox Output
16. Section Eleven — Edge Case Resiliency
17. Section Twelve — Test Isolation and Development Reliability
18. Section Thirteen — Resource Telemetry
19. Section Fourteen — Monitoring Page Data Contract
20. Section Fifteen — Graph and Telemetry Presentation Support
21. Section Sixteen — Security Model
22. Section Seventeen — PS26117 Demonstration Flow Support
23. Section Eighteen — No Fake Sovereignty
24. Section Nineteen — Performance and Concurrency
25. Section Twenty — Observability
26. Section Twenty-One — API Design Requirements
27. Section Twenty-Two — Implementation Order
28. Section Twenty-Three — End-to-End Acceptance Scenario
29. Section Twenty-Four — Strict Engineering Requirements
30. Section Twenty-Five — Final Definition of Success
31. Final Execution Instruction
32. Appendix A — Suggested Technology Mapping
33. Appendix B — Illustrative Data Contracts
34. Appendix C — Suggested SIH Demonstration Script
35. Closing Note for the Implementing Team

---

## HOW TO USE THIS DOCUMENT

This prompt is organized so that it can be consumed top to bottom by an AI agent operating in an existing repository, or split section by section and issued as individual work orders across multiple sessions. Each section is self-contained enough to be handed over independently, but Section Twenty-Two (Implementation Order) defines the sequence in which the work must actually be executed. Do not reorder that sequence to chase an interesting subsystem first — the dependencies are real: telemetry has to exist before sovereignty claims can be verified, and the model runtime has to be stable before agentic orchestration can be trusted to route through it.

Treat every instance of "must" in this document as a hard requirement for Phase 15 sign-off, and every instance of "should" as a strong default that may be adapted to the team's actual repository, provided the underlying principle is preserved and the adaptation is documented in the gap analysis (Section Twenty-Two, Stage Two).

---

## YOUR ROLE

For the duration of this work you are simultaneously:

- **Principal Systems Architect** — responsible for the coherence of the overall runtime, not just the correctness of any one module.
- **Principal Backend Engineer** — responsible for the services, APIs, and data models that make the architecture real.
- **AI Infrastructure Engineer** — responsible for how local models are loaded, scheduled, routed, and retired under real hardware constraints.
- **Agentic Systems Engineer** — responsible for the orchestration graph that turns a user goal into a validated, artifact-producing execution.
- **Local AI Deployment Engineer** — responsible for making every AI capability in this system runnable on-premise, without a silent dependency on a cloud endpoint.
- **Security and Observability Architect** — responsible for making every sovereignty claim this system makes provable, not asserted.

You are responsible for transforming the existing prototype into a technically credible Sovereign On-Premise Agentic AI Workbench that directly and visibly addresses the objectives of PS26117. You must not treat this project as a generic chatbot application, a generic AI dashboard, or a system where "local AI" is a checkbox rather than the architecture's organizing principle.

---

## EXECUTIVE MANDATE

The existing backend has progressed beyond an early prototype. The next objective is not to add more features — it is to establish a coherent Sovereign AI Runtime architecture that a judging panel, and eventually a real MRPL security review, would find defensible under scrutiny. Five principles anchor everything that follows.

### Principle One — Local AI Execution
Sensitive prompts, documents, embeddings, model inference, and agent workloads must be *capable* of remaining entirely within the local deployment environment. "Capable of" is a precise phrase: the architecture must not merely happen to run locally in the demo — it must structurally prevent silent egress of confidential material during normal operation, and any exception (e.g., an explicitly enabled hybrid mode) must be an opt-in configuration state, never a default or a fallback triggered by failure.

### Principle Two — Agentic Execution
The system must not behave like a question-answering chatbot with a nicer UI. It must receive a goal, decompose the required work, select appropriate capabilities, invoke tools, process and validate results, iterate when validation fails, and converge on a delivered artifact. A single large language model call that "sounds agentic" in its prose is not agentic execution — the state transitions must be real and inspectable.

### Principle Three — Multi-Model Capability
The system must not be tightly coupled to one model. Reasoning, coding, vision, embeddings, document processing, and any other supported task category must be able to route to different locally deployed models or local AI services, selected dynamically rather than hardcoded per call site.

### Principle Four — Hardware Awareness
Local GPU resources are limited, and the architecture must know it. It must manage GPU memory, model loading and unloading, concurrent request pressure, and resource contention without ever crashing the application. A workbench that only works when nothing else is happening on the GPU is not hardware-aware.

### Principle Five — Demonstrable Sovereignty
The system must not merely claim to operate locally — it must produce measurable, observable evidence of the relationship between local processing, local requests, external connections, and prohibited cloud AI communication. The system must be able to make the following statement and back it with telemetry, not assertion: *"Sensitive AI workloads are processed using the local AI environment, and the system can visibly demonstrate the network and execution activity associated with that claim."*

---

## ENGINEERING PHILOSOPHY — THE STANDING FILTER

Every feature proposed for Phase 15, no matter how compelling in isolation, must pass through the same nine-question filter before it is prioritized:

1. Does this support the PS26117 problem statement?
2. Does this improve local AI capability?
3. Does this improve agentic execution?
4. Does this improve confidentiality?
5. Does this improve observability?
6. Does this improve real-world reliability?
7. Does this improve the team's ability to demonstrate the solution to judges?
8. Does this work on realistic local hardware — a single consumer or workstation-class GPU, not a data-center cluster?
9. Does this introduce unnecessary cloud dependence, or create a security claim the system cannot actually back up?

If a feature fails questions one through eight, or triggers a "yes" on question nine, it does not get prioritized in this phase, regardless of how impressive it would look in a pitch deck. The project must be technically impressive **and** demonstrable, stable, and understandable to a judge who has five minutes and no patience for hand-waving.

---

## PRIMARY SYSTEM ARCHITECTURE

The system conceptually consists of the following layers, each with a distinct responsibility and a stable interface to its neighbors:

1. **User Interaction Layer** — chat, workspace, canvas, and monitoring surfaces.
2. **Agent Orchestration Layer** — the stateful graph that owns task execution.
3. **Task Planning Layer** — decomposes a goal into an ordered, bounded plan.
4. **Model Routing Layer** — matches a task's capability requirement to an available local model.
5. **Local Model Runtime Layer** — the actual inference services (LLM, vision, embedding, OCR).
6. **Tool Execution Layer** — registered, schema-validated actions the agent can invoke.
7. **Multimodal Processing Layer** — document, image, and drawing ingestion pipelines.
8. **Local Knowledge Layer** — embeddings, vector search, and retrieval.
9. **Artifact Generation Layer** — the subsystem that turns execution results into real deliverables.
10. **Sandbox Execution Layer** — isolated code and command execution.
11. **Resource Management Layer** — GPU/CPU/RAM/VRAM scheduling and contention handling.
12. **Security and Sovereignty Monitoring Layer** — network classification and audit.
13. **Telemetry Layer** — structured, timestamped, sourced metrics and events.
14. **Persistent State Layer** — tasks, workflows, artifacts, and audit history.

### Conceptual Execution Flow

```
User Request
   → Task Understanding
   → Execution Planning
   → Capability Selection
   → Model Selection
   → Context Collection
   → Tool Selection
   → Local Execution
   → Result Validation
   → Iteration (bounded, only when required)
   → Artifact Generation
   → Final Delivery
   [ Telemetry and audit events fire at every arrow above, not just at the endpoints ]
```

The system must not expose private internal model reasoning at any point in this flow. It must instead expose safe, structured execution activity: *understanding request, planning task, selecting local model, reading document, searching local knowledge, invoking vision model, running code, executing tool, validating result, retrying failed action, generating artifact, completing task.* These states are sufficient for transparency and trust-building with a user or a judge. Do not collect, store, or broadcast hidden chain-of-thought — the backend produces structured execution summaries and observable state transitions instead, full stop.


---

## SECTION ONE — SOVEREIGNTY AND LOCAL EXECUTION VERIFICATION

The ability to demonstrate local and sovereign execution is a core requirement of PS26117, not a nice-to-have monitoring page. The architecture must not rely only on frontend counters or manually written application logs — it must establish a trustworthy telemetry pipeline capable of observing relevant network and runtime activity, and it must be honest about the limits of what it can observe.

### 1.1 Platform-Aware Monitoring

Do not assume that one monitoring mechanism works identically across Linux, Windows, and containerized environments — implement platform-aware monitoring adapters instead. The architecture supports four monitoring layers, from most to least authoritative:

- **Application-level request telemetry** — every call the workbench itself makes is logged with source, destination, and classification.
- **Runtime-level AI service telemetry** — the local model runtime (Ollama, vLLM, llama.cpp server, or equivalent) exposes its own request and resource activity.
- **Container or process-level network telemetry** — connection tracking scoped to the workbench's own processes or container namespace.
- **Host-level network telemetry**, only when deployment permissions genuinely allow it.

The monitoring interface must expose the *source* of every metric, and must distinguish measured data, estimated data, and development mock data at the API level, not just in a tooltip. Never present mock values as real measurements — this is the single fastest way to lose credibility with a technical judging panel.

### 1.2 Network Classification

Every observed connection must be classified into one of the following categories, and the classification rule set must be configurable rather than hardcoded, because a real MRPL deployment will have private internal networks that are not automatically "safe" just because they are RFC 1918 addresses:

- Local process communication
- Loopback communication
- Internal infrastructure communication
- Local AI inference communication
- Local knowledge service communication
- Sandbox communication
- External API communication
- External cloud AI communication
- Blocked external communication
- Unknown external communication

The system supports a configurable trusted-network policy. Trusted destinations may include loopback interfaces, configured local subnets, local container networks, approved internal infrastructure services, configured local AI inference services, configured local databases, configured local vector stores, and configured local sandbox environments. Every other destination is treated according to the configured security policy — default-deny for anything not explicitly classified is the correct posture for a sovereignty-focused system.

### 1.3 The Sovereignty Auditor Subsystem

Implement a **Sovereignty Auditor** subsystem responsible for collecting and classifying network activity associated with the workbench. It must be modular and not permanently tied to one OS-level monitoring technology:

```
SovereigntyAuditor (interface)
 ├── LinuxMonitorAdapter        (eBPF / nftables counters / conntrack, when permitted)
 ├── WindowsMonitorAdapter      (ETW / WFP integrations, when available)
 ├── ContainerNetworkAdapter    (namespace-scoped connection accounting)
 ├── ApplicationTelemetryAdapter (in-process request logging — always available)
 └── DevelopmentMockAdapter     (explicitly labeled, never shipped as default)
```

Do not implement unsupported kernel behavior, and do not assume privileged access is always available — the system must degrade gracefully and clearly report its current capability state as one of: **Host Level Monitoring Active**, **Container Level Monitoring Active**, **Application Level Monitoring Active**, **Limited Monitoring Mode**, or **Unavailable**. The UI must never imply kernel-level monitoring is active when only application-level monitoring exists — this single rule protects the entire sovereignty narrative from being an exaggeration.

### 1.4 Audit Event Model

Every observed network event that matters produces a structured audit record containing: timestamp; source process or service identifier (when available); source component; destination category; destination address (when safe to record); destination service; protocol; direction; bytes transferred; request classification; and security decision (Allowed / Blocked / Unknown). The monitoring system must not capture or expose confidential payload contents unless an explicit secure-debugging mode is enabled — the default behavior is metadata-only.

### 1.5 Sovereignty Metrics API

Expose a dedicated API (e.g., `/api/v1/sovereignty/metrics`) providing current and historical values for: local request count; local AI inference request count; internal service request count; external API request count; cloud AI request count; blocked external request count; external data transfer volume; local data transfer volume; current monitoring capability; current security policy state; recent network events; last detected external connection; and last detected cloud AI request. If no external event has occurred, report that honestly rather than presenting a suspiciously perfect zero with no supporting evidence trail. If a category cannot be observed, the API must say so explicitly — e.g. `"cloud_ai_request_monitoring_status": "limited"` — because an honest "we can't fully see this yet" is more defensible under judge or auditor questioning than a false "zero."

### 1.6 Real-Time Monitoring Transport

Use Server-Sent Events or WebSockets so the monitoring page receives incremental updates — never force a full page reload for live data. The telemetry stream carries: resource updates, model runtime updates, agent execution updates, tool execution updates, network events, security events, model loading/unloading events, VRAM changes, error events, and monitoring capability changes. The monitoring page is a live observability surface, not a static report refreshed on a timer.

### 1.7 Network Enforcement

Do not embed host firewall assumptions directly into application startup code. The system supports a configurable network policy defining allowed and prohibited destinations, and where the deployment environment supports network isolation (container network policy, host firewall policy, network namespace policy, enterprise firewall policy), external egress should be blocked at that infrastructure layer — the application layer verifies and reports enforcement state, it does not claim to be the sole guarantor of isolation. The strongest deployable posture is defense in depth: application policy, container policy, host policy, network policy, monitoring, and audit logging working together. Support a **demonstration mode** that visibly shows a local AI request, a local knowledge request, a local tool request, an external request attempt, and a blocked external request side by side — using controlled test endpoints only, and never sending confidential data externally to prove the point.

---

## SECTION TWO — LOCAL MULTI-MODEL RUNTIME

### 2.1 Model Catalog

Do not hardcode model names throughout the backend — implement a persistent **Model Catalog**. Each registered model carries: unique model identifier; display name; provider type; runtime type; model location; capabilities; supported modalities; context limits (when known); estimated and, where available, measured VRAM requirement; CPU-fallback capability; GPU requirement; supported devices; model status (availability, load state, health state); version; and configuration. The capabilities field must support meaningful routing across categories such as general reasoning, code generation, code analysis, vision understanding, document analysis, embeddings, summarization, structured extraction, and tool selection. Routing must evaluate task capability requirements, not just pick "the biggest model available."

### 2.2 Model Router

Implement a **Model Router** that considers task type, required modality, required capability, model availability, current model health, GPU memory availability, estimated queue time, current model load, task priority, and fallback options. The router prefers capable local models, and if the preferred model is unavailable it attempts an appropriate local fallback — it must never silently fall back to a cloud AI service. Cloud fallback stays disabled unless the deployment is explicitly configured for a mode that permits it; the default PS26117 demonstration mode is fully local, no exceptions.

### 2.3 Model Health Management

Every local AI service exposes a health state from the set: Available, Loading, Loaded, Busy, Idle, Unloading, Unavailable, Failed, Degraded. Orchestration must use these states directly — never dispatch work to a model already known to be unavailable.

### 2.4 Resource Manager and GPU-Aware Scheduling

Implement a **Resource Manager** responsible for GPU-aware scheduling. It monitors, where the platform and runtime support it, total VRAM, available VRAM, allocated VRAM, per-model VRAM usage, per-process VRAM usage, model loading state, current inference load, and pending model requests. The system must handle insufficient GPU memory gracefully — it must never allow uncontrolled concurrent model loading, and it must never allow an avoidable GPU out-of-memory crash to take down the workbench.

### 2.5 Model Swap Queue

When a requested model cannot be loaded because GPU resources are occupied, the Resource Manager evaluates, in order of preference: (1) use an already-loaded compatible model; (2) queue the request until resources free up; (3) unload an idle model; (4) move a suitable model to CPU execution where explicitly supported and appropriate; (5) reject the task gracefully with a clear resource-state explanation if no safe path exists. The Resource Manager must never blindly unload a model currently serving an active inference request — eviction respects reference counts or active-request tracking, no exceptions.

### 2.6 Model Runtime Interface and Eviction

Do not assume a specific runtime always supports a particular undocumented command — use provider-specific adapters behind a common interface:

```
ModelRuntimeInterface
 ├── load_model()
 ├── unload_model()
 ├── check_model_status()
 ├── run_inference()
 ├── get_resource_usage()
 └── health_check()
```

Each provider implementation (e.g., an Ollama adapter, a vLLM adapter, a llama.cpp-server adapter) translates these operations into its own supported behavior.

### 2.7 Synchronization and Zero-Downtime Expectation

Use proper asynchronous synchronization — async events, async locks, queues, semaphores, condition variables, timeouts, and cancellation handling. Never use arbitrary sleep delays as a synchronization mechanism. The system must handle concurrent requests arriving during model loading or unloading; requests may wait in a bounded queue and must receive meaningful progress state (*waiting for GPU resources, loading local model, model currently busy, queued for execution*), never indefinite silence — every queued request has a timeout and a cancellation path.

"Zero downtime" here does not mean physically instantaneous model swapping — model loading may legitimately introduce latency. The real requirement is graceful service continuity: the backend process stays alive, independent requests continue where possible, the system never crashes because a model is being swapped, and the user receives accurate execution state even when Time To First Token is elevated because a local model just had to load.


---

## SECTION THREE — AGENTIC ORCHESTRATION CORE

The orchestration layer must support genuine multi-step execution: task understanding, planning, capability selection, model selection, context retrieval, tool selection, tool execution, result inspection, validation, retry, iteration, artifact creation, and final response — through explicit state transitions, not one large opaque model call dressed up as "agentic."

### 3.1 Orchestration Graph

Use a stateful orchestration architecture (LangGraph or an equivalent graph-based orchestration framework). Conceptual states: Receive Request → Analyze Task → Build Plan → Gather Context → Select Model → Select Tool → Execute → Observe Result → Validate → Retry if Required → Create Artifact → Finalize → Complete. The graph supports controlled loops — an agent may execute multiple steps — but every loop is bounded by a maximum step count, a maximum retry count, a timeout, cancellation support, error handling, and a resource budget. The agent must never continue indefinitely; a plan that cannot converge within its budget fails cleanly and reports why.

### 3.2 Execution Trace

Do not expose hidden chain-of-thought. Instead, build a structured **Agent Execution Trace** of safe, observable events: *task started, plan created, selected coding model, selected vision model, retrieved three local documents, executed spreadsheet tool, generated Python file, code execution failed, retrying with corrected input, artifact created, task completed.* Each event carries: task identifier, step identifier, step type, component, start time, end time, duration, status, retry number, parent step, artifact references (when applicable), and error category (when applicable). This trace powers the frontend timeline and agent-activity interface — it must be understandable to a non-expert user, and it must never leak private model reasoning.

### 3.3 Human-in-the-Loop Approval

The agent supports approval checkpoints for high-impact actions when configured — deleting project files, overwriting important files, executing privileged commands, accessing protected directories, changing security configuration, or sending information outside the trusted environment. The orchestration graph supports a **Requires Approval** paused state with the task state persisted; the user approves or rejects with an action description, a risk level, and the requested operation attached. The backend resumes only after valid approval, and rejection safely terminates or redirects the affected execution branch — it never proceeds anyway.

---

## SECTION FOUR — MULTIMODAL DOCUMENT AND KNOWLEDGE PROCESSING

PS26117 must handle more than plain text: PDF documents, scanned PDFs, images, engineering drawings, photographs, office documents, spreadsheets, text files, and code files, all through local services.

### 4.1 Document Processing Pipeline

File validation → file classification → metadata extraction → text extraction → OCR when required → image extraction when required → vision processing when required → chunking → embedding → local indexing → knowledge availability. Source metadata is preserved throughout, and every retrieved piece of information remains traceable back to its source document wherever the format supports it.

### 4.2 Corrupted Document Handling

Document ingestion must never crash the backend. Treat every external parser and native library as potentially unstable, and isolate risky parsing workloads where appropriate. The system detects and handles invalid files, corrupted PDFs, malformed office files, OCR failures, unsupported file types, parser timeouts, and unexpected parser termination — assigning each file a status of Pending, Processing, Completed, Partially Processed, Failed, or Unprocessable, with the failure reason stored and a safe error event surfaced to the UI. If a parser process crashes, the main backend process remains fully operational.

### 4.3 Knowledge Retrieval

Local embeddings, local vector search, metadata filtering, source tracking, and context assembly — the retrieval layer stays entirely local in the sovereign deployment configuration. Do not silently call an external embedding API; that single call would quietly invalidate the entire sovereignty claim for any document that passed through it.

---

## SECTION FIVE — TOOL EXECUTION AND SANDBOXING

The workbench must be able to perform work, not just describe it: file operations, document analysis, spreadsheet operations, code generation, code execution, data analysis, artifact generation, local search, and knowledge retrieval, all through explicitly registered tools. The agent must never execute arbitrary unregistered operations.

### 5.1 Tool Registry

Every tool defines: unique identifier, name, description, input schema, output schema, permission level, execution environment, timeout, resource limits, network policy, supported task types, and health state. The model does not invent arbitrary system commands — every tool call is validated against its schema before execution.

### 5.2 Tool Execution Contract

Validate input → check authorization → check policy → allocate execution environment → execute → capture output → capture errors → enforce timeout → clean resources → return structured result → emit telemetry. No step in this chain is optional, and no step is skipped for "trusted" tools.

### 5.3 Sandbox Execution

Code execution is isolated — never execute arbitrary generated code directly inside the primary backend process. Use an isolated execution environment (a container, a microVM such as Firecracker, or an equivalent) with configurable restrictions: CPU limits, memory limits, execution timeout, filesystem boundaries, network policy, process limits, and workspace isolation. The sandbox is observable: the execution trace shows *sandbox started, code running, output produced, error produced, execution completed, sandbox terminated.* Do not expose unnecessary host privileges to the sandbox under any circumstance.

---

## SECTION SIX — ARTIFACT MANAGEMENT AND REAL DELIVERABLES

The workbench must produce actual artifacts — text files, Markdown, code files, reports, structured data, spreadsheets, documents, presentations, generated images, and charts — because performing real work rather than only producing conversational answers is the entire point of an *agentic* workbench.

### 6.1 Artifact Event Model

When an artifact is created, emit a structured **Artifact Created** event containing: task identifier, artifact identifier, artifact type, file name, workspace location, creation time, generating step, preview capability, and download/open capability. The frontend receives this event and presents the generated file directly; artifacts remain associated with their originating project workspace, never floating free of their provenance.

---

## SECTION SEVEN — WORKFLOW ORCHESTRATION AND CANVAS COMPATIBILITY

A node-based workflow canvas may exist on the frontend, but the backend must never execute arbitrary frontend-supplied code — it compiles workflow definitions through a validated intermediate representation instead.

### 7.1 Workflow Definition and Validation

The frontend submits a structured graph of nodes, edges, node configuration, tool references, model references, input mappings, and output mappings. The backend validates: node types, tool references, model references, input/output compatibility, absence of unauthorized operations, absence of cycles unless explicitly supported, execution limits, maximum graph size, and — critically — the absence of any arbitrary code injection path.

### 7.2 Workflow Compiler

Valid workflow definitions compile into executable orchestration graphs where nodes map only to registered capabilities: local model call, tool execution, document retrieval, artifact generation, validation, conditional branch, or approval checkpoint. The compiler rejects unsupported nodes with a useful validation error, and every workflow execution produces deterministic execution records: workflow identifier, execution identifier, node states, start/end times, durations, outputs, errors, and retry state, which the frontend uses to visualize progress.


---

## SECTION EIGHT — REAL-TIME FRONTEND-BACKEND CONTRACTS

Do not create APIs only to satisfy visual components — every API must correspond to meaningful backend state. The system supports task execution events, agent state events, model runtime events, tool events, artifact events, resource telemetry, network telemetry, security events, and errors, all through a standardized **Event Envelope**:

```
EventEnvelope
 ├── event_id
 ├── event_type
 ├── timestamp
 ├── project_id
 ├── task_id
 ├── execution_id
 ├── parent_id
 ├── component
 ├── status
 ├── payload
 ├── duration
 └── sequence_number
```

The event system supports ordering via `sequence_number`, and the frontend must be able to reconnect after a temporary disconnection and resynchronize state via replay or state-sync rather than losing track of what happened while it was offline. Do not depend on animation timing as a source of truth — the backend is always the source of truth, and the frontend renders what the backend reports.

---

## SECTION NINE — WORKSPACE AND FILE SYSTEM MANAGEMENT

The project workspace provides controlled file operations: directory listing, create directory, create file, read file, write file, rename, move, delete, tree view, and artifact discovery — all constrained to an approved workspace root. Never trust a client-supplied absolute path. Prevent directory traversal, validate every path against the canonical workspace root, and reject any attempt to escape it. Each project workspace is logically isolated from every other; the frontend may present a developer-friendly file tree, but the backend remains solely responsible for access control — the UI is never a substitute for a server-side check.

---

## SECTION TEN — REAL-TIME TERMINAL AND SANDBOX OUTPUT

The frontend may provide a terminal-like experience representing the isolated execution environment — it must never expose the primary host shell by default. The system streams real-time stdout/stderr from approved sandbox tasks through controlled streaming, supporting connection, authentication, project isolation, sandbox isolation, output streaming, cancellation, disconnection handling, timeout handling, and cleanup. The frontend must never obtain unrestricted shell access to the host machine, under any UI convenience justification.

---

## SECTION ELEVEN — EDGE CASE RESILIENCY

Assume that any external process, local model, parser, queue message, database connection, or GPU operation can fail — because on real hardware, during a live demo, at least one of them will.

### 11.1 Poison Messages
A malformed task message must not put a worker into an infinite failure loop. The worker validates the message, catches validation errors, records the failure, moves the message to a dead-letter queue (or equivalent), acknowledges the original message correctly, emits an operational error event, and continues processing future tasks. The malformed message stays available for debugging rather than vanishing.

### 11.2 LLM Structured Output Failure
Local models can produce malformed structured output. The orchestration layer validates model-generated structured data; on a parse failure it captures the validation error, preserves the safe raw output for debugging where permitted, requests a corrected structured response, and limits retries to a configurable maximum. The agent never retries forever.

### 11.3 Model Service Failure
A local model service may stop unexpectedly, fail health checks, error, time out, become overloaded, or lose GPU access. The system detects the failure, marks the runtime state appropriately, stops sending new work to the failed service, attempts configured recovery, uses a local fallback capability when one exists, and fails gracefully when no valid local fallback exists — it never silently reaches for a cloud endpoint as a shortcut.

### 11.4 GPU Out of Memory
GPU exhaustion must never crash the entire backend. The Resource Manager detects insufficient capacity before attempting risky operations wherever possible, and otherwise queues requests, unloads idle models when policy permits, uses compatible loaded models, or rejects safely — always recording the resource event and never concealing an out-of-memory condition from telemetry.

### 11.5 Database Connection Saturation
The database layer uses controlled connection pooling with defined pool limits, timeouts, overflow policy, and connection health checks. Do not retry database operations blindly, and keep transactions safe under retry.

### 11.6 Queue Failure
If queue or event infrastructure becomes unavailable, the backend enters a controlled degraded state and reports the problem — tasks never silently disappear. Use durable persistence or recovery mechanisms wherever possible.

### 11.7 Network Partition
Local infrastructure services may become temporarily unavailable. The system distinguishes *local service unavailable*, *network telemetry unavailable*, *external network blocked*, and *unknown network state* — it does not interpret every failed request as a security violation, which would poison the sovereignty metrics with false positives.

---

## SECTION TWELVE — TEST ISOLATION AND DEVELOPMENT RELIABILITY

Tests must never contaminate development state.

- **Test containers** created during tests receive a unique test namespace (e.g., a `pytest-sandbox-<uuid>` naming convention), and the test system tracks every resource it creates.
- **Test cleanup** executes even when tests fail — teardown removes test containers, temporary networks, temporary volumes (where appropriate), temporary workspaces, and test artifacts, identified by controlled labels or prefixes so unrelated development containers are never touched.
- **Test database** usage is dedicated and explicit — never the primary development database. The test lifecycle is: create or start the test database, apply schema migrations, run tests, clean test state, stop temporary services when appropriate. Never rely on accidental environment configuration to keep tests isolated.

---

## SECTION THIRTEEN — RESOURCE TELEMETRY

The monitoring page is not a Windows Task Manager clone — it collects information relevant specifically to the Sovereign AI Workbench: CPU utilization, GPU utilization, RAM utilization, VRAM utilization (current and time-averaged), per-model VRAM usage where available, inference activity, model load state, agent activity, tool activity, queue depth, task throughput, local request count, external API request count, cloud AI request count, blocked request count, and external/local data transfer volumes. These metrics are sourced from a defined **Resource Telemetry Interface** with implementations for GPU, CPU, memory, model-runtime, and network telemetry providers, plus an explicitly labeled development mock provider. The UI receives timestamped measurements, and historical graph data is generated from actual samples or clearly identified simulated samples — never invented values presented as live system data.

---

## SECTION FOURTEEN — MONITORING PAGE DATA CONTRACT

The monitoring page is evidence infrastructure. It must answer: what is currently running; which models are active; what resources are being consumed; what the agent is currently doing; which tools are active; how much GPU memory is in use; whether requests are remaining local; whether external APIs are being contacted; whether cloud AI services are being contacted; whether data is leaving the trusted environment; and what level of monitoring is currently active. It distinguishes **measured zero**, **not observed**, **unavailable**, **unknown**, **blocked**, and **allowed** as genuinely different states — "External API Requests: 0" is only a valid statement when the monitoring system can actually observe that traffic category. If monitoring is unavailable, the page reports "monitoring unavailable," never a substitute zero. This distinction is the difference between a credible sovereignty claim and a decorative one.

---

## SECTION FIFTEEN — GRAPH AND TELEMETRY PRESENTATION SUPPORT

The backend provides efficient time-series data for area charts and live telemetry visualizations. Each sample carries timestamp, metric name, value, unit, source, and — where applicable — measurement confidence. The backend supports rolling windows (recent minute, recent five minutes, recent thirty minutes, session history) and bounded buffers with aggregation where appropriate — it never sends unlimited historical data through every real-time update. Animation is a frontend concern; telemetry correctness is a backend concern, and the backend never generates artificial animation values to make a chart look smoother than the underlying data actually is.

---

## SECTION SIXTEEN — SECURITY MODEL

The system operates on least privilege: every component receives only the permissions its function requires. The primary backend does not require unrestricted host privileges. Sandbox containers remain isolated, and network monitoring agents are separated from application services where practical. Host-level monitoring is optional and deployment-aware. Secrets are never hardcoded and sensitive configuration is stored securely; sensitive prompts, confidential document contents, and credentials are not logged by default — audit logs prioritize metadata. The system supports configuration-driven deployment modes — development, demonstration, secure local deployment, and enterprise deployment — that may differ in observability and infrastructure but must each clearly communicate what guarantees they actually provide.


---

## SECTION SEVENTEEN — PS26117 DEMONSTRATION FLOW SUPPORT

The architecture must support a convincing live demonstration of the complete lifecycle of a realistic task. Illustrative flow:

1. A user provides a confidential document (e.g., an MRPL-style maintenance report or engineering drawing).
2. The workbench accepts the document and processes it locally.
3. OCR or vision processing is invoked locally when required.
4. The agent gathers relevant context from the local knowledge base.
5. The Model Router selects an appropriate local capability for each sub-task.
6. The agent executes the required tools.
7. The result is validated.
8. The agent generates a real artifact.
9. The user receives the completed deliverable.

Simultaneously, the monitoring page shows local model activity, GPU usage, VRAM usage, agent activity, tool execution, local requests, external request count, cloud AI request count, and external data transfer — and it must create a **visible, causal relationship** between the work being performed and the telemetry being observed. When the local LLM starts inference, model activity, GPU utilization, and VRAM utilization should visibly change and a local-inference event should appear. When the vision model is used, the monitoring system reflects that specific model's activity. When an artifact is generated, the execution trace records the artifact event in the same moment. This correlation is the single most persuasive thing the demo can show — the monitoring page must never display unrelated statistics that don't map to what the workbench is actually doing right now.

---

## SECTION EIGHTEEN — NO FAKE SOVEREIGNTY

The following patterns are prohibited unless explicitly and visibly marked as development mocks: a hardcoded external-request count of zero; a hardcoded cloud-AI-request count of zero; static GPU usage pretending to be live telemetry; static VRAM usage pretending to represent local model consumption; fake local-model activity; fake network logs; fake security scores; fake external-request blocking. Any mock telemetry used purely for interface development must be isolated behind a clearly labeled development provider that the monitoring UI can identify and disclose. The final SIH demonstration prioritizes actual observable activity wherever the environment permits it — a slightly less polished but genuinely real dashboard beats a polished but fabricated one every time a judge asks a follow-up question.

---

## SECTION NINETEEN — PERFORMANCE AND CONCURRENCY

The backend supports concurrent users and tasks within realistic hardware limits, using queues, semaphores, backpressure, timeouts, cancellation, resource budgeting, and model-request serialization where required. It must avoid GPU overload, unbounded memory growth, infinite agent loops, infinite retries, unbounded event buffers, unbounded WebSocket queues, and unbounded artifact generation. Every long-running operation supports cancellation and timeout behavior — no exceptions for "this one's usually fast."

---

## SECTION TWENTY — OBSERVABILITY

Use structured logs with correlation identifiers: task IDs, execution IDs, model IDs, and tool IDs threaded through every log line touching a given request. Errors are categorized as Validation Error, Resource Error, Model Error, Tool Error, Network Error, Security Policy Error, Parser Error, Database Error, Queue Error, or Unknown Error. Internal stack traces are never exposed to normal frontend users — store detailed diagnostics server-side and surface safe, human-readable error summaries to the UI.

---

## SECTION TWENTY-ONE — API DESIGN REQUIREMENTS

All APIs are versioned. All request payloads are validated. All response schemas are typed. Errors are clear and never leak unnecessary implementation detail. The following conceptual API groups should exist: Task APIs, Workflow APIs, Model Catalog APIs, Model Runtime APIs, Tool APIs, Workspace APIs, Artifact APIs, Telemetry APIs, Sovereignty APIs, Monitoring APIs, and Approval APIs. Reuse the existing project architecture where possible — do not create duplicate service layers without a documented justification in the gap analysis.

---

## SECTION TWENTY-TWO — IMPLEMENTATION ORDER

Do not modify the entire backend simultaneously. Work proceeds in controlled stages, and no stage begins before the previous one's outputs exist.

**Stage One — Inspect.** Read the complete current project and its architecture documentation. Read the UI Design skill/spec only for understanding frontend contracts and consistency requirements. Inspect existing backend modules, model runtime integration, orchestration implementation, telemetry implementation, network monitoring implementation, database schema, queue infrastructure, and sandbox architecture. Identify what already exists before changing anything.

**Stage Two — Gap Analysis.** Determine which requirements already exist, which are partially implemented, and which conflict with the existing architecture. Do not duplicate functionality that already works — document every deliberate deviation from this prompt here.

**Stage Three — Interfaces and Contracts.** Define or refine: telemetry interfaces, network auditor interfaces, model runtime interfaces, model catalog interfaces, tool registry interfaces, artifact interfaces, event schemas, and execution trace schemas — before writing the implementations behind them.

**Stage Four** — Implement core sovereignty telemetry.
**Stage Five** — Implement resource-aware model management.
**Stage Six** — Strengthen agent orchestration and safe execution tracing.
**Stage Seven** — Strengthen multimodal ingestion.
**Stage Eight** — Strengthen sandbox and tool execution.
**Stage Nine** — Implement workflow compilation and frontend contracts.
**Stage Ten** — Implement fault tolerance.
**Stage Eleven** — Implement test isolation.
**Stage Twelve** — Run integration tests.
**Stage Thirteen** — Run a complete SIH demonstration scenario end to end.

Do not declare this phase complete until the complete workflow has been tested end to end against Section Twenty-Three below.

---

## SECTION TWENTY-THREE — END-TO-END ACCEPTANCE SCENARIO

The implementation must pass a realistic confidential-work scenario end to end: the user submits a document or project task; the system creates a task; the Agentic Orchestrator builds an execution plan; the system selects a suitable local model; the document is processed locally; relevant context is retrieved from local knowledge; a local tool executes; the agent validates the result; a real artifact is generated and appears in the workspace; the execution trace shows the major actions taken; and the monitoring system simultaneously shows active model, agent activity, tool activity, resource consumption, VRAM consumption, local request activity, external request state, cloud AI request state, and external data-transfer state. Throughout, the workbench and backend remain stable, no uncontrolled process crashes, and no sensitive data is intentionally transmitted to an untrusted external service.

---

## SECTION TWENTY-FOUR — STRICT ENGINEERING REQUIREMENTS

Inspect before modifying. Understand the existing architecture before refactoring. Preserve working functionality and prefer incremental refactoring. Use typed models and validated schemas. Use asynchronous synchronization correctly, bounded queues, cancellation, and timeouts. Implement graceful degradation. Separate development mocks from production telemetry, visibly. Do not hardcode model names or capabilities throughout the orchestration layer — use the dynamic Model Catalog. Do not assume unlimited GPU memory, a specific GPU model, universal kernel-level telemetry support, privileged container access, or guaranteed external network connectivity. Do not silently use cloud AI as a fallback. Do not expose hidden chain-of-thought — expose safe structured execution traces instead. Do not execute arbitrary generated code in the primary backend, expose unrestricted host filesystem access, or allow path traversal. Do not create fake security metrics, fake local-inference evidence, or fake network logs. Do not use arbitrary sleep calls as synchronization, infinite retries, infinite agent loops, or unbounded resource usage.

---

## SECTION TWENTY-FIVE — FINAL DEFINITION OF SUCCESS

This phase succeeds only when the project behaves as a credible Sovereign On-Premise Agentic AI Workbench: capable of receiving a complex task, planning it, selecting suitable local capabilities, using multiple local AI capabilities where required, processing multimodal information, using controlled tools, executing work, validating results, recovering from expected failures, generating real deliverables, managing limited GPU resources, dynamically managing model availability, remaining stable during resource contention, providing safe real-time execution visibility and meaningful monitoring, distinguishing local processing from external communication, distinguishing measured values from unavailable monitoring, and providing observable evidence supporting its local and sovereign deployment claims. It must not depend on a visually impressive but technically fake dashboard, and it must not depend on cloud AI services for its core PS26117 demonstration workflow. The final result must be technically coherent, demonstrable, stable, hardware-aware, secure by design, and directly responsive to the purpose of PS26117.

---

## FINAL EXECUTION INSTRUCTION

Act as the Principal Engineer responsible for completing this phase. Before writing code, inspect the complete existing implementation and identify what already exists — do not replace working systems unnecessarily, and do not introduce duplicate architecture. Create a detailed internal implementation plan before making changes, then execute it incrementally, validating after every major subsystem change.

After implementation: run unit tests; run integration tests; test failure scenarios; test GPU resource pressure; test model unavailability; test malformed tool outputs; test malformed queue messages; test corrupted documents; test sandbox failure; test telemetry failure; test monitoring degradation; test external request classification; test project workspace isolation; test artifact generation; test agent cancellation; and test approval checkpoints. Finally, execute a complete end-to-end PS26117 demonstration workflow.

The final implementation must demonstrate not only that the system can answer a user — it must demonstrate that the system can perform real work; that local AI capabilities can be orchestrated together; that the workbench can manage constrained local hardware; that the system can process confidential workloads entirely within the trusted environment; that there is a visible, provable difference between local processing and external communication; and that the workbench provides credible observable evidence rather than unsupported security claims.

The final objective is not to build another AI chatbot. **The final objective is to build a practical Sovereign On-Premise Agentic AI Workbench capable of performing confidential enterprise work through local models, local tools, controlled agentic orchestration, real artifact generation, hardware-aware execution, and verifiable operational telemetry.** This is the definition of success for Phase 15.

---

## APPENDIX A — SUGGESTED TECHNOLOGY MAPPING (NON-BINDING)

This mapping is a starting point for Stage One's inspection, not a mandate — if the existing repository already uses a different but equivalent tool for a given role, keep it and record the choice in the gap analysis rather than migrating for its own sake.

| Layer | Candidate local-first technology | Why it fits a sovereignty-first workbench |
|---|---|---|
| Local LLM / VLM runtime | Ollama, vLLM, or llama.cpp server | Runs open-weight models entirely on-premise; exposes a local HTTP surface the Model Runtime Interface can wrap |
| Orchestration graph | LangGraph, or a hand-rolled finite-state graph | Gives explicit, inspectable state transitions instead of one opaque call |
| Vector store | Qdrant, Chroma, or pgvector | All runnable fully on-premise with no managed-cloud dependency |
| Task queue | Redis Streams, RabbitMQ, or Celery+Redis | Supports dead-letter handling and bounded queues natively |
| Sandbox isolation | Docker with strict resource limits, or Firecracker microVMs | Process- and filesystem-isolated code execution without full host access |
| Network telemetry (Linux) | nftables counters, conntrack, or eBPF via a library such as bcc | Observes real connection activity without requiring a full IDS stack |
| Real-time transport | WebSockets (e.g., via FastAPI/Starlette) or Server-Sent Events | Both are sufficient; pick whichever the existing frontend already integrates |
| Relational store | PostgreSQL with connection pooling (e.g., pgbouncer or the ORM's own pool) | Mature pooling, overflow, and health-check semantics |
| OCR / vision | A local OCR engine (e.g., Tesseract or a local vision-language model) | Keeps document understanding inside the trust boundary |

---

## APPENDIX B — ILLUSTRATIVE DATA CONTRACTS

These are illustrative shapes, not a final schema — Stage Three (Section Twenty-Two) is where the team locks the real ones down against the existing codebase.

**Model Catalog Entry**
```json
{
  "model_id": "local-coder-7b",
  "display_name": "Local Coding Model 7B",
  "provider_type": "ollama",
  "capabilities": ["code_generation", "code_analysis"],
  "modalities": ["text"],
  "context_limit": 32768,
  "vram_estimate_mb": 8192,
  "vram_measured_mb": null,
  "cpu_fallback": false,
  "status": { "availability": "available", "load_state": "unloaded", "health": "unknown" }
}
```

**Sovereignty Audit Event**
```json
{
  "timestamp": "2026-09-07T10:14:03Z",
  "source_component": "model_router",
  "destination_category": "local_ai_inference",
  "destination_service": "ollama:11434",
  "protocol": "http",
  "direction": "outbound",
  "bytes_transferred": 4096,
  "classification": "local_ai_inference",
  "decision": "allowed"
}
```

**Agent Execution Trace Event**
```json
{
  "task_id": "task_9f21",
  "step_id": "step_04",
  "step_type": "tool_execution",
  "component": "sandbox_tool",
  "start_time": "2026-09-07T10:14:05Z",
  "end_time": "2026-09-07T10:14:07Z",
  "status": "succeeded",
  "retry_number": 0,
  "parent_step": "step_03",
  "artifact_refs": ["artifact_1123"]
}
```

**Event Envelope (WebSocket/SSE payload)**
```json
{
  "event_id": "evt_88a1",
  "event_type": "model.loading",
  "timestamp": "2026-09-07T10:14:01Z",
  "project_id": "proj_01",
  "task_id": "task_9f21",
  "execution_id": "exec_02",
  "parent_id": null,
  "component": "resource_manager",
  "status": "in_progress",
  "sequence_number": 145
}
```

---

## APPENDIX C — SUGGESTED SIH DEMONSTRATION SCRIPT

A judging panel typically gives a working system more credit when the demonstration narrates cause and effect rather than clicking through screens. A workable structure for a five-to-seven-minute live demo:

1. **Open on the monitoring page at rest** — show the honest "no external or cloud AI activity observed" state, with the monitoring-capability indicator visible, before any task is submitted.
2. **Submit a realistic confidential document** (e.g., a maintenance report or engineering drawing) through the workspace.
3. **Narrate the plan as it appears** in the execution trace — task understanding, model selection, document processing.
4. **Point at the monitoring page reacting in real time** — GPU/VRAM utilization rising, a local-inference event appearing, the request classified as local AI inference rather than external.
5. **Show a tool executing** (e.g., a spreadsheet or code tool) and the sandbox lifecycle events appearing in the trace.
6. **Trigger one deliberate failure** (e.g., a malformed input) to show retry and graceful recovery — this is often more convincing to judges than a flawless run, because it proves the resiliency claims in Section Eleven rather than asserting them.
7. **Show the generated artifact** landing in the workspace and being opened.
8. **Close on the sovereignty metrics view**, explicitly calling out local request count, external request count (and what, if anything, was blocked), and the current monitoring capability level — this is the moment that answers "how do we know this is actually local" before a judge has to ask it.

---

## CLOSING NOTE FOR THE IMPLEMENTING TEAM

This document intentionally repeats certain constraints — no hidden chain-of-thought, no fake telemetry, no silent cloud fallback, no unbounded loops — across several sections. That repetition is deliberate: these are the exact places where a team under hackathon time pressure is most tempted to cut a corner that looks harmless in isolation but collectively undermines the sovereignty story the whole project is built to tell. When time is short, cut scope, not honesty — a smaller system that can prove every claim it makes will out-perform a larger one that cannot, both in front of judges and in front of a real MRPL security reviewer.
