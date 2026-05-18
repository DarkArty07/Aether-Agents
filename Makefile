# ==============================================================================
# Aether Agents v0.8.0 — Makefile
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

# ── Health Check ───────────────────────────────────────────────────────────────

.PHONY: doctor
doctor: ## Verify installation (python, venv, hermes, olympus, gpu)
	@echo "═══ Aether Agents — Doctor ═══"
	@echo ""
	@echo -n "  Python 3.11+:    " && (python3 -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}.{v.micro}")' 2>/dev/null || echo "NOT FOUND")
	@echo -n "  Venv exists:     " && ([ -d home/.venv-hermes ] && echo "✓ home/.venv-hermes" || echo "✗ MISSING")
	@echo -n "  Hermes binary:   " && (home/.venv-hermes/bin/hermes --version 2>/dev/null || echo "NOT FOUND")
	@echo -n "  Olympus import:  " && (home/.venv-hermes/bin/python -c "import olympus_v3.server; print('✓ olympus_v3')" 2>/dev/null || echo "✗ FAILED")
	@echo -n "  NVIDIA GPU:      " && (nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "NOT AVAILABLE")
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
		home/.venv-hermes/bin/python -m pytest tests/ -v; \
	else \
		echo "No tests/ directory found — skipping"; \
	fi

# ── Help ───────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help