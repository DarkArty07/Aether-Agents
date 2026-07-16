# ==============================================================================
# Aether Agents v0.17.0 — Makefile
# Common development targets
# ==============================================================================

# ── Setup & Install ────────────────────────────────────────────────────────────

.PHONY: setup
setup: ## Run full setup (venv, packages, config, wrappers)
	bash scripts/setup.sh

.PHONY: update
update: ## Update repo and upgrade dependencies
	bash scripts/update.sh

# ── Gateway ────────────────────────────────────────────────────────────────────

.PHONY: gateway
gateway: ## Delegate to start-gateway.sh (pass extra args: make gateway ARGS="start")
	bash scripts/start-gateway.sh $(ARGS)

# ── Honcho (Memory Provider) ───────────────────────────────────────────────────

.PHONY: setup-honcho
setup-honcho: ## Setup Honcho: submodule, .env, detected Compose runtime up
	bash scripts/setup-honcho.sh

.PHONY: honcho-up honcho-down honcho-logs
honcho-up honcho-down honcho-logs: COMPOSE = $(shell bash scripts/setup-honcho.sh --detect-compose)
honcho-up: ## Start Honcho services with the detected Compose runtime
	$(COMPOSE) up -d

honcho-down: ## Stop Honcho services with the detected Compose runtime
	$(COMPOSE) down

honcho-logs: ## Follow Honcho API logs with the detected Compose runtime
	$(COMPOSE) logs -f api

# ── Python interpreter ────────────────────────────────────────────────────────

# Prefer the legacy project venv. For pip-installed Hermes, use the interpreter
# colocated with the hermes executable; otherwise fall back to python3.
PYTHON ?= $(shell if [ -x home/.venv-hermes/bin/python ]; then \
	printf '%s' home/.venv-hermes/bin/python; \
elif command -v hermes >/dev/null 2>&1; then \
	hermes_bin="$$(command -v hermes)"; hermes_dir="$$(dirname "$$hermes_bin")"; \
	if [ -x "$$hermes_dir/python" ]; then printf '%s' "$$hermes_dir/python"; \
	elif [ -x "$$hermes_dir/python3" ]; then printf '%s' "$$hermes_dir/python3"; \
	else command -v python3; fi; \
else command -v python3; fi)

# ── Health Check ───────────────────────────────────────────────────────────────

.PHONY: doctor
doctor: ## Verify installation (python, hermes, olympus, gpu)
	@echo "═══ Aether Agents — Doctor ═══"
	@echo ""
	@echo "  Python interpreter: $(PYTHON)"
	@echo -n "  Python 3.11+:       " && ($(PYTHON) -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}.{v.micro}")' 2>/dev/null || echo "NOT FOUND")
	@echo -n "  Hermes binary:      " && (hermes --version 2>/dev/null || echo "NOT FOUND")
	@echo -n "  Olympus import:     " && ($(PYTHON) -c "import olympus_v3.server; print('✓ olympus_v3')" 2>/dev/null || echo "✗ FAILED")
	@echo -n "  NVIDIA GPU:         " && (nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "NOT AVAILABLE")
	@echo ""

# ── Cleanup ────────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove venv and __pycache__ directories
	rm -rf home/.venv-hermes/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned home/.venv-hermes/ and __pycache__"

# ── Tests ──────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run test suite (if tests/ exists)
	@if [ -d tests ]; then \
		$(PYTHON) -m pytest tests/ -v; \
	else \
		echo "No tests/ directory found — skipping"; \
	fi

# ── Help ───────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help