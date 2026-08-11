# ==============================================================================
# Aether Agents v0.23.0.dev0 — Makefile
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
doctor: ## Verify Hermes, current roster, and the 15-tool source surface
	@echo "═══ Aether Agents — Doctor ═══"
	@echo ""
	@echo "  Python interpreter: $(PYTHON)"
	@echo -n "  Python 3.11+:       "; $(CLEAN_PYTHON_ENV) $(PYTHON) -c 'import sys; v=sys.version_info; assert v >= (3, 11); print(f"{v.major}.{v.minor}.{v.micro}")' 2>/dev/null || { echo "✗ FAILED"; exit 1; }
	@echo -n "  Hermes binary:      "; $(CLEAN_PYTHON_ENV) $(HERMES) --version 2>/dev/null || { echo "✗ FAILED"; exit 1; }
	@echo -n "  Product assets:     "; $(CLEAN_PYTHON_ENV) $(PYTHON) -c "from pathlib import Path; root=Path('.'); profiles={p.parent.name for p in (root/'home/profiles').glob('*/config.yaml.template')}; assert (root/'VERSION').read_text().strip() == '0.23.0.dev0'; assert (root/'home/config.yaml.template').is_file(); assert profiles == {'hefesto', 'daedalus', 'ictinus'}; assert not any((root/'home/profiles'/name).exists() for name in ('ariadna', 'athena', 'etalides')); print('✓ root config + 3 allowed profiles')" 2>/dev/null || { echo "✗ FAILED"; exit 1; }
	@echo -n "  MCP source surface: "; PYTHONPATH=src $(CLEAN_PYTHON_ENV) $(PYTHON) -c "from aether_mcp import __version__; from aether_mcp.server import create_server; tools=tuple(t.name for t in create_server()._tool_manager.list_tools()); assert __version__ == '0.23.0.dev0'; assert len(tools) == 15; print('✓ 0.23.0.dev0 / 15 tools')" 2>/dev/null || { echo "✗ FAILED"; exit 1; }
	@echo -n "  NVIDIA GPU:         "; gpu="$$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"; if [ -n "$$gpu" ]; then echo "$$gpu"; else echo "NOT AVAILABLE"; fi
	@echo ""

# ── Cleanup ────────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove repository build and Python cache artifacts; preserve live runtime
	find src scripts tests -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .ruff_cache/
	@echo "✓ Cleaned source/test caches; live runtime preserved"

# ── Tests ──────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run test suite (if tests/ exists)
	@if [ -d tests ]; then \
		PYTHONPATH=src $(PYTHON) -m pytest tests/ -v; \
	else \
		echo "No tests/ directory found — skipping"; \
	fi

.PHONY: mcp-smoke
mcp-smoke: ## Run the current Aether MCP stdio process through clean EOF
	PYTHONPATH=src $(PYTHON) -m aether_mcp </dev/null

.PHONY: runtime-status
runtime-status: ## Read the named local Aether MCP installation status
	$(PYTHON) scripts/aether_mcp/status.py --hermes-home "$(CURDIR)/home"

.PHONY: runtime-doctor
runtime-doctor: ## Check the installed runtime and report stale owned resources
	$(PYTHON) scripts/aether_mcp/doctor.py --hermes-home "$(CURDIR)/home"

# ── Help ───────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
