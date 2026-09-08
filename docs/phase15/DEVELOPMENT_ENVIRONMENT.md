# Development Environment

**Status:** PARTIALLY VERIFIED - Local Python environment verified, Docker infrastructure not available

---

# Canonical Development Model

**Backend:** Local Python venv development with PostgreSQL database service
**Frontend:** Not currently deployed (frontend code not present in repository)
**Database:** PostgreSQL via docker-compose test-db service (localhost:5433)
**Model Runtime:** Ollama via docker-compose 
**Sandbox:** Docker containers (requires Docker Desktop)
**Redis:** docker-compose redis service (for worker pipeline)

---

# Primary Development Workflow

1. **Unit Tests:** Run in local Python venv without external services
2. **Integration Tests:** Require docker-compose services (database, redis) and Docker Desktop
3. **E2E Tests:** Require full application stack (backend API, worker, database, redis, Ollama, Docker sandbox)
4. **Development:** Use local Python environment with database service for backend development

---

# Python Environment

## Python Version

**Verified:** Python 3.14.2
**Location:** `C:\Users\gurug\AppData\Local\Python\pythoncore-3.14-64\python.exe`

## Virtual Environment Location

**Status:** Not currently required for development
**Venv:**  Always use this for testing and development
**Note:** Project dependencies installed in venv Python environment

## Is venv Required?

**Yes** - Current development uses local venv Python installation
**Recommendation:** Consider creating project-specific venv for better isolation

## Dependency Installation Method

**Primary:** `pip install -r requirements.txt`
**Note:** Some packages (paddlepaddle) have platform-specific installation issues on Windows

**Recent Installations:**
- pyjwt (for JWT authentication)
- python-magic-bin (for file type detection, Windows-specific)
- python-docx, openpyxl (for document processing)
- langgraph, langchain-core (for agentic orchestration)

---

# Docker Environment

## Docker's Role

**Intended Purpose:** 
- Database services (PostgreSQL, Redis)
- Sandbox execution environment
- Full application stack deployment
- Integration testing infrastructure

## Compose Files

**Primary:** `docker-compose.yml` in project root
**Services:** 
- `db` (PostgreSQL with pgvector)
- `redis` (Redis for worker pipeline)
- `test-db` (Dedicated test database on port 5433)

## Services

| Service | Port | Purpose | Status |
|---|---|---|---|
| db | 5432 | Main PostgreSQL database | Available |
| test-db | 5433 | Dedicated test database | Available |
| redis | 6379 | Redis for worker pipeline | Available |
| ollama | 11434 | Local model runtime | External (requires installation) |

## Startup Commands

**Start services:** `docker-compose up -d db redis test-db`
**Stop services:** `docker-compose down`
**View logs:** `docker-compose logs -f [service]`

**Current Status:** Docker Desktop not available in current environment

---

# Test Environment

## Unit Tests

**Environment:** Local Python (no external services required)
**Command:** `cd backend && python -m pytest tests/unit/ -v --tb=short`
**Status:** ✅ 15/15 passing
**Dependencies:** None (uses test database fixtures)

## Integration Tests

**Environment:** Requires docker-compose services (database, redis)
**Command:** `cd backend && python -m pytest tests/integration/ -v --tb=short`
**Status:** ⚠️ 25/32 passing (7 blocked by Docker/GPU/worker requirements)
**Dependencies:** PostgreSQL, Redis, Docker Desktop (for sandbox tests)

## E2E Tests

**Environment:** Requires full application stack
**Command:** `cd backend && python -m pytest tests/e2e/ -v --tb=short`
**Status:** ❌ Blocked by infrastructure requirements
**Dependencies:** Full stack (backend API, worker, database, redis, Ollama, Docker sandbox)

## Contract Tests

**Environment:** Mix of unit and integration test requirements
**Command:** `cd backend && python -m pytest contract_tests/ -v --tb=short`
**Status:** ⚠️ Partially validated
**Dependencies:** Varies by test category

## Isolation Requirements

**Test Database:** Dedicated `test-db` service on port 5433
**Sandbox Namespace:** Random container names with pytest-sandbox prefix
**Cleanup:** Manual cleanup required for test artifacts

---

# Environment Variables

## Source Files

**Primary:** `.env` in project root
**Backend:** `backend/.env` (development overrides)

## Required Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/ps26117

# Redis
REDIS_URL=redis://localhost:6379

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# JWT Secret
JWT_SECRET=your-secret-key-here

# Model Configuration
AGENT_MAX_STEPS=10
AGENT_MAX_RETRIES=2
```

## Secret Handling

**Current Status:** Development secrets in `.env` files
**Production:** Use environment variables or secret management
**Security:** Do not commit `.env` files with real secrets

---

# Ports and Services

| Service | Host | Port | Environment | Status |
|---|---|---|---|---|
| Backend API | localhost | 8000 | Local Python | Available |
| PostgreSQL (main) | localhost | 5432 | Docker | Available |
| PostgreSQL (test) | localhost | 5433 | Docker | Available |
| Redis | localhost | 6379 | Docker | Available |
| Ollama | localhost | 11434 | External service | Requires installation |
| Sandbox | localhost | N/A | Docker | Requires Docker Desktop |

---

# Recommended Commands

## Start

```bash
# Start database services
docker-compose up -d db redis test-db

# Run database migrations
cd backend
alembic upgrade head

# Start backend (if needed)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Stop

```bash
# Stop services
docker-compose down

# Clean up volumes (optional)
docker-compose down -v
```

## Backend Tests

```bash
# Unit tests only
cd backend
python -m pytest tests/unit/ -v --tb=short

# Integration tests (requires services)
python -m pytest tests/integration/ -v --tb=short

# All tests (requires full infrastructure)
python -m pytest tests/ -v --tb=short
```

## Integration Tests

```bash
# Requires docker-compose services running
docker-compose up -d db redis test-db
cd backend
python -m pytest tests/integration/ -v --tb=short
```

---

# Commands That Must Not Be Used Casually

- **pip install** without checking current environment state
- **docker-compose up** without checking existing running services
- **Global package installation** when project venv should be used
- **Running tests against wrong database** (main vs test)
- **Starting services on occupied ports** without checking conflicts

---

# Common Environment Problems

## Problem: Docker Desktop not available
**Symptoms:** Sandbox tests fail, container-related errors
**Cause:** Docker Desktop not installed or not running
**Resolution:** Install Docker Desktop or use environment without Docker-dependent features

## Problem: Port conflicts
**Symptoms:** Services fail to start, connection refused
**Cause:** Another process using required ports (5432, 5433, 6379, 8000)
**Resolution:** Check port usage, stop conflicting services, or reconfigure ports

## Problem: Database connection failures
**Symptoms:** Connection refused, authentication errors
**Cause:** Database service not running, wrong port, wrong credentials
**Resolution:** Ensure docker-compose services are running, check DATABASE_URL

## Problem: Ollama not available
**Symptoms:** Model inference failures, connection refused
**Cause:** Ollama not installed or not running
**Resolution:** Install Ollama and start service with `ollama serve`

## Problem: Python dependency conflicts
**Symptoms:** Import errors, version conflicts
**Cause:** Global Python installation conflicts, wrong Python version
**Resolution:** Use project-specific venv, verify Python version matches requirements

---

# Last Verified

**Date:** 2026-09-07
**Milestone:** Unit test environment validation
**Verification Evidence:** Unit tests pass (15/15) in local Python environment
**Commands Tested:** `python -m pytest tests/unit/ -v --tb=short`

---

# Known Limitations

1. **Docker Desktop:** Not available in current environment, limiting sandbox and container-based testing
2. **GPU Hardware:** Not available, limiting resource manager and GPU-related testing
3. **Worker Process:** Not running, limiting worker pipeline and task queue testing
4. **Full Stack:** Not deployed, limiting E2E and integration testing
5. **Frontend:** Not present in repository, limiting full-stack validation

These limitations are documented in `INFRASTRUCTURE_CONSTRAINTS.md`