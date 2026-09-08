# AGENTFLOW AGENT/COORDINATOR ARCHITECTURE INVESTIGATION

## 4. CURRENT AGENT INVENTORY

The current system has shifted from procedural, hard-coded agents to a state-driven, orchestrated workflow graph utilizing LangGraph.

**Legacy Agents (Deprecated/Phased Out)**
- **Planner (`backend/app/agents/planner.py`)**: Legacy procedural planning agent relying on an old `TierRouter`.
- **Validator (`backend/app/agents/validator.py`)**: Legacy procedural evaluation agent.

**Modern Agent Roles (LangGraph Nodes in `backend/app/agents/graph.py`)**
- **Planning Node (`plan_node`)**: Generates an execution plan based on the tool catalog.
- **Execution Node (`execute_node`)**: Safe execution boundary delegating tool calls to the `Executor` with policy enforcement.
- **Observation Node (`observe_node`)**: Incorporates step outcomes into the system context.
- **Reasoning/Validation Node (`reason_node`)**: Assesses if the objective is complete, triggering retries or final answers.

## 5. AGENT INVENTORY TABLE

| Agent / Node | Path | Primary Responsibility | Input Contract | Output Contract |
|---|---|---|---|---|
| Planner (Legacy) | `agents/planner.py` | Break objective down into tool steps | `objective: str` | `PlanSchema(steps=[])` |
| Validator (Legacy) | `agents/validator.py` | Validate agent run outcomes | `task`, `agent_run` | `ValidationResult` |
| `plan_node` | `agents/graph.py` | Generate execution plan | `AgentState` | updated `AgentState["plan"]` |
| `execute_node` | `agents/graph.py` | Execute tool securely via `Executor` | `AgentState` | updated `AgentState["step_results"]` |
| `observe_node` | `agents/graph.py` | Add context of tool outcomes | `AgentState` | updated `AgentState["context"]` |
| `reason_node` | `agents/graph.py` | Validate if task is COMPLETE or CONTINUE | `AgentState` | updated `AgentState["status"]` |

## 6. TRACE A REAL TASK (API to completion)

1. **Creation**: Task is created via API (`backend/app/tasks/service.py:TaskService.create_task`), saving a `Task` (status: `CREATED`), emitting `task.created` and `task.queued`.
2. **Execution Claim**: Worker pulls task via `TaskRunner.run` (`backend/app/tasks/runner.py`), updating status to `RUNNING` and claiming a lease.
3. **Orchestration**: If `task_type == "agentic_workflow"`, `AgentOrchestrator.run` is invoked.
4. **Graph Execution**: 
   - State initialized with `AgentState`.
   - `plan_node` requests the model to generate a plan from `get_tool_catalog()`.
   - `execute_node` uses `Executor.execute_step()` to run tools securely, enforcing schema checks and `PolicyEngine.check()`.
   - Tool requires approval? `InMemoryApprovalGate` sets `awaiting_approval=True`, pausing execution.
   - `observe_node` logs the tool outcome.
   - `reason_node` evaluates completion. If not COMPLETE, routes to `execute` or `plan`.
5. **Completion**: Orchestrator returns success/failure payloads.
6. **Finalization**: `TaskRunner` updates task to `COMPLETED` or `FAILED`, emitting `task.completed` or `task.failed`.

## 7. DEEPLY AUDIT WorkflowGraph

- **File**: `backend/app/agents/graph.py`
- **Architecture**: A LangGraph `StateGraph` implementation bounding execution tightly.
- **Components**: `plan_node`, `execute_node`, `observe_node`, `reason_node`.
- **Strengths**: True state machine preventing runaway loops. Fully traces execution using `ExecutionTraceSink` emitting `ExecutionTraceEvent`s containing *no model reasoning*.
- **Weaknesses**: Hardcoded max limits (`max_steps=10`, `max_retries=2`) in state initialization. Graph does not natively yield on streaming events to a frontend yet.

## 8. DEEPLY AUDIT AgentOrchestrator

- **File**: `backend/app/agents/orchestrator.py`
- **Architecture**: Synchronous wrapper around the asynchronous `WorkflowGraph`.
- **Dependencies**: Injects `db_session`, `redis_client`, `OllamaRuntime`, `ExecutionTraceSink`, `InMemoryApprovalGate`, and `Executor` into the graph.
- **Contract**: Maps raw `task.input_payload` to `AgentState` and maps final `AgentState` back to a serialized dict for `task.result_payload`. Safe fallback if exceptions leak out.

## 9. DEEPLY AUDIT Planner

- **Status**: The standalone `planner.py` file is *legacy/deprecated*.
- **Actual Implementation**: Planning is now heavily integrated as the `plan_node` inside `WorkflowGraph`.
- **Mechanism**: Serializes the tool registry to JSON schema, prepends conversation history, and prompts the local Ollama runtime to produce a JSON array of `AgentPlan` steps using `pydantic` validation. Model inference is purely local (`ModelRouter` + `OllamaRuntime`).

## 10. DEEPLY AUDIT AgentState

- **Location**: `backend/app/agents/graph.py:AgentState` (TypedDict)
- **Fields**: `objective`, `project_id`, `task_id`, `execution_id`, `context`, `plan`, `current_step_index`, `step_results`, `step_count`, `max_steps`, `retry_count`, `max_retries`, `final_answer`, `status`, `awaiting_approval`, `approval_id`, `failure_reason`.
- **Critique**: Tightly coupled to task runs. Contains pure execution state. Follows Master Prompt requirements by isolating private chain-of-thought from the state that gets serialized.

## 11. DEEPLY AUDIT EXECUTOR

- **File**: `backend/app/agents/executor.py`
- **Architecture**: The strict boundary between agent intent and host execution.
- **Stages**:
  1. **Registry Verification**: Checks tool existence.
  2. **Policy Enforcement**: `PolicyEngine.check()` enforces sandboxing rules.
  3. **Schema Validation**: Strict Pydantic parsing.
  4. **Safe Execution**: `asyncio.wait_for` wrapping tool execution catching `TimeoutError` and `SecurityError`.
- **Telemetry**: Emits `agent.step.started/completed` and synchronous `log_action_sync` for security auditing.

## 12. DEEPLY AUDIT TASK RUNNER / WORKER

- **File**: `backend/app/tasks/runner.py`
- **Architecture**: Database polling/lease-based task execution. Claims tasks by updating `status="RUNNING"`, setting `worker_id` and `lease_expiry`.
- **Agent Integration**: Conditionally branches on `task_type == "agentic_workflow"` to instantiate `AgentOrchestrator`, otherwise performs a simple direct LLM call.
- **Faults**: Explicitly catches exceptions, updating status to `FAILED` and emitting failure events.

## 13. INTER-AGENT COMMUNICATION ANALYSIS

- **Current Implementation**: No direct agent-to-agent pub/sub messaging. Communication is entirely mediated by the shared `AgentState` within the single LangGraph instance. 
- **Observations**: The "agents" (plan, execute, reason) communicate by mutating the `AgentState` dict and traversing the graph edges. Multi-agent swarms do not exist yet.

## 14. CONTRACT ANALYSIS

- **Models**: `ModelInferenceRequest`, `ModelCatalogEntry`, `ModelStatus` decouple orchestrator from raw LLMs.
- **Trace Events**: `ExecutionTraceEvent` explicitly captures execution metadata *without* private reasoning, writing to `SqlAlchemyExecutionTraceSink`.
- **Task Payload**: Loose schema (`JSONB`) on the `Task` model, relying on upstream validation.

## 15. EVENT-DRIVEN ORCHESTRATION ANALYSIS

- **Mechanism**: The system emits heavy telemtry via `EventEnvelope` onto Redis streams via `publish()`.
- **Triggering**: Orchestration is currently *not* event-driven. The worker polls for tasks and synchronously runs `WorkflowGraph.ainvoke`.
- **Finding**: Events (`task.started`, `agent.step.completed`) are currently used for observability, not orchestration flow control.

## 16. RESOURCE-AWARE AGENT EXECUTION

- **Routing**: `ModelRouter` explicitly requires `ResourceManager` in `run()`. It leases VRAM (`resource_manager.lease`) before invoking `runtime.run_inference()`.
- **Agents**: `plan_node` and `reason_node` use `ModelInferenceRequest` which passes through this resource boundary, fulfilling the Phase 15 local-first memory-aware requirement.

## 17. VALIDATION / RECONCILIATION ARCHITECTURE

- **Mechanism**: Handled dynamically by the `reason_node` in the workflow graph.
- **Process**: The node analyzes tool outputs and explicitly outputs `COMPLETE` or `CONTINUE`.
- **Failure Handling**: If a tool fails, it increments `retry_count`. If `max_retries` exceeded, halts. If the LLM produces bad JSON, the system intercepts `pydantic` exceptions and routes to failure.

## 18. HUMAN APPROVAL ARCHITECTURE

- **Mechanism**: Handled in `execute_node` via `InMemoryApprovalGate` (`backend/app/agents/approval.py`).
- **Process**: Checks `tool_name in approval_required_tools`. If true, mutates state: `awaiting_approval = True`. The graph yields.
- **Persistence**: Currently uses a transient `requests: dict[UUID, ApprovalRequest]` in memory, but a SQLAlchemy schema (`ApprovalRequestRecord`) exists in `models.py` suggesting a migration to persistence is pending.

## 19. TASK SPECIFICATION ANALYSIS

- **Storage**: Tasks stored in `tasks` table with `input_payload: JSONB`.
- **Usage**: Mapped directly to `objective` string in the Orchestrator. No strong Pydantic parsing of the objective occurs between the database and the agent graph.

## 20. PERSISTENCE ARCHITECTURE

- **Task/Runs**: Postgres `tasks` table. Legacy `agent_runs` and `plan_steps` tables still exist.
- **Trace History**: `execution_trace_records` explicitly stores execution history to support the UI without leaking AI prompt context.
- **Workflow State**: State (`AgentState`) is built in-memory per run and not checkpointed natively. If the server crashes during LangGraph execution, the task stalls until the worker lease expires and a retry is issued.

## 21. TARGET ARCHITECTURE MAPPING

- **Achieved**: Use of LangGraph, secure tool execution boundaries, VRAM-aware inference routing, separation of private reasoning from execution traces.
- **Missed**: In-memory approval gate instead of DB-backed; lacking proper event-driven suspension (graph just exits on approval request without standard LangGraph checkpointing).

## 22. PRESERVATION ANALYSIS

- **Preserve**: `Executor` policy enforcement and strict Pydantic validation are robust. `ModelRouter` integration is clean.
- **Remove**: Legacy `planner.py` and `validator.py` files. Legacy `agent_runs` and `plan_steps` ORM models.

## 23. REFACTORING RISK ANALYSIS

- **High Risk**: Moving from synchronous `TaskRunner` blocking on `graph.ainvoke` to a truly async/checkpointed event-driven architecture will require ripping out the lease polling mechanism.
- **Low Risk**: Deleting legacy agent files. Refactoring `ApprovalGate` to use SQLAlchemy.

## 24. ARCHITECTURAL GAP ANALYSIS

- The graph lacks native LangGraph checkpointer integration (`langgraph.checkpoint`). State is lost on container restart.
- Human-in-the-loop approvals are in-memory, causing approvals to drop if the API restarts.
- Orchestrator blocks the worker thread for the entire task lifecycle.

## 25. MOST IMPORTANT QUESTION (Can it be evolved incrementally?)

**Yes.** The separation of concerns is already mostly correct. The LangGraph `WorkflowGraph` encapsulates the logic beautifully. To evolve it incrementally:
1. Wire a `PostgresSaver` checkpointer into LangGraph.
2. Swap `InMemoryApprovalGate` for a DB-backed implementation.
3. Migrate `TaskRunner` to trigger graph continuations on events rather than blocking on `ainvoke`.

## 26. PROPOSED TARGET RESPONSIBILITY BOUNDARIES

- **WorkflowGraph**: Purely defines edges, nodes, and state schemas.
- **Checkpointer**: Manages graph suspension/resumption state.
- **Executor**: Purely enforces security/policy boundaries against tools.
- **Approval Service**: Dedicated domain managing asynchronous human authorization via DB.
- **Router/Runtime**: Isolated capability providing inference without business context.

## 27. FINAL VERDICT

Strictly evaluating against the Master Prompt:
The Agent Orchestrator architecture **IS LARGELY ALIGNED** with the target design. The use of LangGraph correctly modernizes the procedural legacy code. The integration with the ModelRouter properly respects the strict resource boundaries. The telemetry properly scrubs model thoughts. However, it requires immediate updates to persistence (checkpointers, approvals) to achieve the promised fault-tolerance and true event-driven execution required by Stage Ten.
