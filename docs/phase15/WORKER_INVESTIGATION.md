# Worker Pipeline Investigation

## Issue Identified

The worker pipeline test (`test_worker_direct_llm_execution`) fails because the worker is connected to a different database than the test.

### Database Connection Mismatch

**Test Environment:**
- Uses `TEST_DATABASE_URL = postgresql+asyncpg://admin:password@localhost:5433/sovereign_ai_test`
- Configured in `backend/tests/conftest.py` line 11
- Creates tasks in the test database (localhost:5433)

**Worker Environment:**
- Uses `DATABASE_URL = postgresql+asyncpg://admin:password@db:5432/sovereign_ai`
- Configured in `docker-compose.yml` line 84
- Worker looks for tasks in the main database (db:5432)

### Problem Flow

1. Test creates task in test database (localhost:5433)
2. Worker polls main database (db:5432) for tasks
3. Worker never sees the task created by the test
4. Test times out waiting for task completion

### Evidence

**Worker Environment Variables:**
```
DATABASE_URL=postgresql+asyncpg://admin:password@db:5432/sovereign_ai
REDIS_URL=redis://redis:6379/0
OLLAMA_BASE_URL=http://ollama:11434
```

**Test Environment Variables:**
```
TEST_DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5433/sovereign_ai_test
REDIS_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
```

### Worker Logs Analysis

Worker logs show:
- Worker is running and healthy
- Outbox dispatcher is polling correctly
- Task recovery loop is running
- No task consumption events are logged
- Only database polling with ROLLBACK (no tasks found)

This confirms the worker is not seeing the tasks created by the test.

## Root Cause

The test is designed to validate the full worker pipeline (API → Outbox → Redis Stream → Worker → LLM → DB), but the test environment and worker environment are using different databases. This is a configuration issue, not an implementation issue.

## Solution Options

### Option 1: Fix Test Configuration (RECOMMENDED)
Configure the test to use the same database as the worker for integration testing, or configure a test-specific worker that uses the test database.

### Option 2: Fix Worker Configuration
Configure the worker to be database-agnostic and allow runtime database configuration.

### Option 3: Skip Test Until Fixed
Document this as a configuration gap and skip the test until database alignment is resolved.

## Next Action

The most appropriate fix is to update the test configuration to align with the worker's database connection, or to create a test-specific worker configuration. This is a project configuration issue, not a fundamental implementation problem.