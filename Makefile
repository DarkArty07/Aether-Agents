# ==============================================================================
# Aether Agents v0.22.0 — Makefile
# Common development targets
# ==============================================================================

# ── Setup & Install ────────────────────────────────────────────────────────────

.PHONY: setup
setup: ## Install Hermes and generate Aether configs and wrappers
	bash scripts/setup.sh

.PHONY: update
update: ## Update repo, Hermes, and generated configuration
	bash scripts/update.sh

# ── Gateway ────────────────────────────────────────────────────────────────────

.PHONY: gateway
gateway: ## Delegate to start-gateway.sh (pass extra args: make gateway ARGS="start")
	bash scripts/start-gateway.sh $(ARGS)

# ── Python interpreter ────────────────────────────────────────────────────────

# Prefer the project venv. For pip-installed Hermes, use the interpreter
# colocated with the hermes executable; otherwise fall back to python3.
PYTHON ?= $(shell if [ -x home/.venv-hermes/bin/python ]; then \
	printf '%s' home/.venv-hermes/bin/python; \
elif command -v hermes >/dev/null 2>&1; then \
	hermes_bin="$$(command -v hermes)"; hermes_dir="$$(dirname "$$hermes_bin")"; \
	if [ -x "$$hermes_dir/python" ]; then printf '%s' "$$hermes_dir/python"; \
	elif [ -x "$$hermes_dir/python3" ]; then printf '%s' "$$hermes_dir/python3"; \
	else command -v python3; fi; \
else command -v python3; fi)

HERMES := $(shell if [ -x home/.venv-hermes/bin/hermes ]; then \
	printf '%s' home/.venv-hermes/bin/hermes; \
	elif command -v hermes >/dev/null 2>&1; then command -v hermes; \
	else printf '%s' hermes; fi)

CLEAN_PYTHON_ENV := env -u PYTHONPATH -u HERMES_PYTHON_SRC_ROOT

# ── Health Check ───────────────────────────────────────────────────────────────

.PHONY: doctor
doctor: ## Verify Hermes and Aether product assets
	@echo "═══ Aether Agents — Doctor ═══"
	@echo ""
	@echo "  Python interpreter: $(PYTHON)"
	@echo -n "  Python 3.11+:       "; $(CLEAN_PYTHON_ENV) $(PYTHON) -c 'import sys; v=sys.version_info; assert v >= (3, 11); print(f"{v.major}.{v.minor}.{v.micro}")' 2>/dev/null || { echo "✗ FAILED"; exit 1; }
	@echo -n "  Hermes binary:      "; $(CLEAN_PYTHON_ENV) $(HERMES) --version 2>/dev/null || { echo "✗ FAILED"; exit 1; }
	@echo -n "  Product assets:     "; $(CLEAN_PYTHON_ENV) $(PYTHON) -c "from pathlib import Path; root=Path('.'); profiles=list((root/'home/profiles').glob('*/config.yaml.template')); assert (root/'VERSION').is_file(); assert (root/'home/config.yaml.template').is_file(); assert len(profiles) == 6; assert not list((root/'home/profiles').glob('*/plugins/aether')); print('✓ root config + 6 profiles; no native runtime plugin')" 2>/dev/null || { echo "✗ FAILED"; exit 1; }
	@echo -n "  NVIDIA GPU:         "; gpu="$$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"; if [ -n "$$gpu" ]; then echo "$$gpu"; else echo "NOT AVAILABLE"; fi
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
		PYTHONPATH=src $(PYTHON) -m pytest tests/ -v; \
	else \
		echo "No tests/ directory found — skipping"; \
	fi

.PHONY: mcp-smoke
mcp-smoke: ## Run the default-off Aether MCP stdio process through clean EOF
	PYTHONPATH=src $(PYTHON) -m aether_mcp </dev/null

# ── Help ───────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
