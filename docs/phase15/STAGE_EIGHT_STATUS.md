# Stage Eight Status Report

**STAGE:** Eight — Tool Execution and Sandbox Boundary

**PRE-FLIGHT ITEMS CLOSED THIS STAGE:** Stage Seven status and ledger were reviewed. Existing sandbox restrictions were spot-checked: `--network=none`, read-only root, CPU/memory/PID limits, dropped capabilities, no-new-privileges, output limits, cancellation cleanup, and filename traversal checks are present.

**ENTRY CRITERIA MET:** Yes. Section Five, the ledger, gap analysis, interface contracts, and prior stage reports were reviewed.

**WHAT WAS BUILT:** `backend/app/tools/base.py` now exposes tool ID, permission, environment, resource, network, task capability, health, timeout, and approval metadata in the planner catalog. `backend/contract_tests/test_stage_eight_tools.py` adds registry metadata, sandbox path escape, and unregistered-tool policy tests.

**NO-FAKE-CAPABILITY CHECK:** Pass for the changed boundary. An unregistered tool is denied, and a workspace escape is rejected before Docker starts. Existing Docker timeout/cancellation behavior remains physical-integration territory; this Windows session did not claim a live Docker timeout result.

**TESTS ADDED:** Three isolated tests covering tool contract metadata, path traversal rejection, and fail-closed unregistered-tool policy.

**TEST RESULT:** Pass — `3 passed in 1.71s`.

**DEVIATIONS FROM THE MASTER PROMPT:** Full terminal streaming, sandbox lifecycle trace events, deployment privilege reduction, and auditor integration remain open. Existing sandbox execution was not rewritten without a live Docker validation environment.

**LEDGER UPDATES:** Tool catalog metadata and pre-Docker path rejection closed; terminal/lifecycle/auditor and least-privilege items remain open.

**OPEN QUESTIONS FOR THE HUMAN TEAM:** Confirm the production sandbox control boundary because the worker currently requires root/Docker socket access; confirm the terminal streaming transport contract for Stage Nine.

**EXIT CRITERIA MET:** Yes for this bounded Stage Eight checkpoint; remaining deployment and terminal work is explicitly carried forward.