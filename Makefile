# Development commands for JointCheck's current prototype scope.

.PHONY: help sample check test demo batch build-pages record-demo clean

INPUT ?= data/sample-gate-request.jsonl
OUTPUT ?= -

help:
	@echo "Available commands:"
	@echo "  make sample   - Run the synthetic offline gate sample and focused tests"
	@echo "  make check    - Run backend tests, Ruff, and the frontend production build"
	@echo "  make test     - Run the backend test suite"
	@echo "  make demo     - Start the prototype API on 0.0.0.0:8000 (no API key needed)"
	@echo "  make build-pages - Build the offline GitHub Pages frontend"
	@echo "  make record-demo - Record a 2:45 Playwright demo (requires preview, Chromium, ffmpeg)"
	@echo "  make batch    - Evaluate JSONL measurement assertions (INPUT=... OUTPUT=...)"
	@echo "  make clean    - Remove virtualenvs, caches, and build artifacts"

sample:
	cd backend && uv run --extra dev pytest tests/test_gate.py tests/test_schemas.py -v
	python jobs/run_gate_batch.py data/sample-gate-request.jsonl

check:
	cd backend && uv run --extra dev ruff check app tests ../jobs
	cd backend && uv run --extra dev pytest -v
	cd frontend && npm ci && npm run build

test:
	cd backend && uv run --extra dev pytest tests/ -v

demo:
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

build-pages:
	cd frontend && npm ci && npm run build

record-demo:
	cd frontend && npm run record:demo

batch:
	python jobs/run_gate_batch.py "$(INPUT)" --output "$(OUTPUT)"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf backend/.venv frontend/node_modules frontend/dist
