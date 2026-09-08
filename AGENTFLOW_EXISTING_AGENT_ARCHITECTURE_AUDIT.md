# AGENTFLOW EXISTING AGENT ARCHITECTURE AUDIT

**Inspection Date:** 2026-09-07
**Evaluator:** Principal Agentic Systems Architect
**Target:** `c:\Users\gurug\project-root` (Phase 14 baseline)

## 1. Executive Summary
This document provides an evidence-based architectural audit of the current AgentFlow / SIH26117 backend repository. The evaluation determines the real state of the agentic implementations, orchestration mechanisms, multi-model execution, and overall alignment with the intended Phase 15 architecture.

## 2. Identify Every Existing Agent
Based on inspection of the `backend/app/agents/` and `backend/app/tasks/` directories, the following agent-related entities exist:
*   **`WorkflowGraph`**: The primary operational agent. It is a LangGraph `StateGraph` implementation located in `agents/graph.py` that encapsulates planning, execution, observation, and reasoning nodes.
*   **`Executor`**: A specialized tool execution boundary agent located in `agents/executor.py` responsible for policy checking, schema validation, timeout enforcement, and execution tracing.
*   **`TaskRunner`**: The core worker component in `tasks/runner.py` that leases tasks and delegates them to the `AgentOrchestrator` or executes direct LLM calls.
*   **Legacy Components**: `planner.py` and `validator.py` contain legacy `Planner` and `Validator` classes that have been functionally superseded by the `WorkflowGraph` nodes but remain in the codebase.

## 3. Build the Existing Agent Inventory

| Agent / Component | Implementation File | Role / Responsibility | Specialization |
| :--- | :--- | :--- | :--- |
| **WorkflowGraph** | `app/agents/graph.py` | Orchestrates the primary task loop. Generates plans, delegates to tools, observes output, and reasons about completion. | **Generic.** It acts as a monolithic ReAct-style agent rather than a specialized worker. |
| **Executor** | `app/agents/executor.py` | Executes registered tools inside or outside sandboxes. Enforces schemas, policies, and captures safe execution traces. | **Specialized.** Strict boundary enforcer. |
| **TaskRunner** | `app/tasks/runner.py` | Leases PostgreSQL tasks via Redis queues and triggers the `AgentOrchestrator`. | **Infrastructure.** |
| **AgentOrchestrator** | `app/agents/orchestrator.py` | Binds the `WorkflowGraph` execution loop to the task payload, initiating the state machine. | **Orchestrator.** |

## 4. Determine Current Orchestration Model
*   **Implementation:** The system uses a state machine orchestration model powered by LangGraph. The `WorkflowGraph` defines four cyclic nodes: `plan_node`, `execute_node`, `observe_node`, and `reason_node`.
*   **State Management:** State is managed via a typed dictionary `AgentState` containing `objective`, `plan`, `step_results`, `retry_count`, and `status`.
*   **Verdict:** **Verified by implementation.** The orchestration is not an unconstrained "while True" loop. It actively uses LangGraph, caps steps via `max_steps` and `max_retries`, and cleanly exits.

## 5. Determine Whether Current Agents Are Actually Specialized
*   **Implementation:** The current implementation relies on a single `WorkflowGraph` to handle all agentic tasks by dynamically selecting tools from a global `TOOL_REGISTRY`.
*   **Verdict:** **Verified by implementation.** The agents are **merely generic/monolithic**, not truly specialized. There is no network of distinct agents (e.g., CodingAgent, ResearchAgent) collaborating. The Phase 15 architecture requires a shift toward specialization, but currently, it is a single capable generalist.

## 6. Evaluate Against Intended AgentFlow Architecture (10 rules)
Based on the Master Prompt and Gap Analysis, the 10 core principles of the AgentFlow architecture evaluate as follows:
1.  **Stateful Graph Execution:** **Verified.** Implemented via LangGraph.
2.  **Explicit Planning:** **Verified.** `plan_node` translates objectives into Pydantic-validated tool calls.
3.  **No Private Reasoning Leaks:** **Partially Implemented.** Traces are emitted, but raw exceptions/planning failures sometimes leak instead of safe internal summaries.
4.  **Observable State Transitions:** **Verified.** State updates trigger events to the trace sink.
5.  **Bounded Execution:** **Verified.** Iterations and tool timeouts are bounded.
6.  **Strict Tool Boundaries:** **Verified.** `agents/executor.py` provides registry, policy, schema, and timeout boundaries.
7.  **Human-in-the-Loop:** **Verified.** `ApprovalGate` and paused state machine states are implemented.
8.  **Hardware Awareness:** **Verified.** `ResourceManager` limits admission based on NVML metrics.
9.  **Dynamic Multi-Model Routing:** **Partially Implemented.** `ModelRouter` selects by capability, but lacks a persistent catalog and active CPU swap queues.
10. **Demonstrable Sovereignty:** **Not Found / Insufficient.** The system assumes container isolation prevents egress, but lacks actual kernel/host telemetry to cryptographically or observably prove local-only processing.

## 7. Examine Task Specification
*   **Implementation:** Tasks are specified in the `Task` PostgreSQL model. Task specification is flat—usually a `prompt` and an optional `system` instruction string inside `input_payload`.
*   **Verdict:** **Verified.** Tasks do not yet support complex hierarchical workflow canvases, though the architecture plans for "Workflow Compilation" in later stages.

## 8. Examine Event Architecture
*   **Implementation:** Events rely on the Transactional Outbox pattern. `publisher.py` writes `EventRecord` and `OutboxEvent` to PostgreSQL atomically. `dispatcher.py` pushes these to Redis Streams, which the worker consumes. Events stream to frontends via SSE/WebSockets (`Envelope` format).
*   **Verdict:** **Verified.** Highly robust and aligned with enterprise distributed systems.

## 9. Examine Model Routing
*   **Implementation:** `router_v2.py` hosts a `ModelRouter` that dynamically matches tasks to models based on required capabilities (e.g., `["tool_calling"]`, `["embedding"]`).
*   **Verdict:** **Partially Implemented.** The routing logic is sound, but the `InMemoryModelCatalog` heavily relies on hardcoded capabilities instead of a persistent, dynamically updatable catalog.

## 10. Examine Resource Management
*   **Implementation:** The `ResourceManager` (in `resource_manager.py`) reads GPU state using `pynvml`. It requires models to lease VRAM before loading. If VRAM is exhausted, requests are queued or bounded.
*   **Verdict:** **Verified by implementation.** It genuinely prevents catastrophic OOMs by failing safely or queueing, demonstrating strong hardware awareness.

## 11. Examine State Architecture
*   **Implementation:** Transient state is stored in LangGraph's `AgentState` and memory. Durable state is persisted in PostgreSQL across `Task`, `ExecutionTraceEvent`, and `ToolExecution` tables. Active worker leases are tracked to allow crash recovery.
*   **Verdict:** **Verified.** The separation of transient graph state and durable audit state is effective.

## 12. Examine Validation
*   **Implementation:** Inside `graph.py`, the `reason_node` calls a local model to assess tool outputs, returning `COMPLETE` or `CONTINUE`. Failed tool validations increment a `retry_count`.
*   **Verdict:** **Verified.** Validation is automated via self-reflection prompts bounded by retry limits.

## 13. Examine Human Intervention
*   **Implementation:** Tool execution pauses if the requested tool is in `approval_required_tools`. The graph enters an `awaiting_approval` state via `InMemoryApprovalGate` and yields control back.
*   **Verdict:** **Verified.** The human-in-the-loop mechanism is structurally sound.

## 14. Examine Monitoring and Provenance
*   **Implementation:** Provenance uses `trace_sink` (`SqlAlchemyExecutionTraceSink`) to append `ExecutionTraceEvent`s.
*   **Verdict:** **Partially Implemented.** As highlighted in `GAP_ANALYSIS.md`, artifact provenance is missing, and sovereignty auditing/metrics (verifying data hasn't leaked to cloud APIs) do not fully exist.

## 15. Identify Architecture Gaps (CURRENT, TARGET, GAP ANALYSIS)
*   **CURRENT:** Monolithic agent orchestrator, in-memory model catalog, Docker-socket bound worker, untested sovereignty claims.
*   **TARGET:** Workflow compiler, persistent multi-model runtime, secure sandboxing, undeniable hardware network telemetry, artifact provenance.
*   **GAP:** The worker has root access to the Docker socket to spin up sandboxes, violating least-privilege. Sovereignty relies on trust rather than telemetry. Artifact generation isn't tightly bound to execution traces.

## 16. Identify What NOT To Change
*   **Transactional Outbox:** The PostgreSQL to Redis Stream pipeline is resilient and should not be replaced.
*   **Executor Boundary:** The Pydantic validation, registry checking, and timeout execution in `executor.py` is enterprise-grade.
*   **Resource Manager Foundation:** The VRAM admission controller (`pynvml` logic) is a highly differentiated feature that must be preserved.

## 17. Identify the Most Important Risk
**The Worker Privilege Model:** The `worker` container requires access to the host's `/var/run/docker.sock` and runs as root to execute sandbox environments. While the sandbox itself drops privileges, a compromised worker has total control over the host Docker daemon. This is a severe violation of the Master Prompt's security and sovereignty guidelines.

## 18. Final Architecture Verdict
**PARTIALLY ALIGNED.**
The foundation is extremely strong and much more advanced than a typical LLM prototype. The use of LangGraph, VRAM admission control, and transactional outboxes provides a robust architecture. However, it fails to achieve full alignment due to a lack of observable network telemetry to prove its sovereignty claims, the presence of a monolithic (rather than specialized) agent graph, incomplete artifact provenance, and critical sandbox privilege issues. The project should continue into Phase 15 implementation using this stable baseline.
