# Makefile
.PHONY: up down migrate seed demo test export-openapi docs-dir

docs-dir:
	mkdir -p docs

up:
	docker compose up -d

down:
	docker compose down -v

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m scripts.seed_demo_data

demo: up
	@echo "Waiting for databases to be ready..."
	sleep 5
	$(MAKE) migrate
	$(MAKE) seed
	@echo "========================================================"
	@echo "🚀 SOVEREIGN AI WORKBENCH DEMO READY"
	@echo "API URL: http://localhost:8000"
	@echo "Docs:    http://localhost:8000/docs"
	@echo "Token:   supersecret-demo-token"
	@echo "========================================================"

test:
	docker compose up -d db redis ollama
	@echo "Waiting for services to initialize..."
	sleep 5
	cd backend && pytest tests/ -v -p no:anyio

export-openapi: docs-dir
	curl -s http://localhost:8000/openapi.json > docs/openapi.json
	@echo "✅ OpenAPI schema exported to docs/openapi.json"