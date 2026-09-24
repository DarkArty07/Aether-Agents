# OC79-DOCS — As-Built Documentation, Capability Registry, and Policy Manifest Evidence

**Unit**: OC79-DOCS, role Implementer.
**Authority**: Objective Contract `oc_79b55027e7c3688d@v1`
(SHA-256 `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), base commit
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`, and Supervisor breakdown
`specs/001-aether-v1-productization/tasks-oc79.md` (commit `f71a3677`).
**Scope**: In-scope documentation sentence; AC5 (docs half); tasks-oc79.md section 106.
**Compatibility conclusion**: `patch`.

---

## 1. Summary of documentation deliverables

1. **`docs/getting-started.md`**:
   - Updated initialization guidance: `aether init` accepts an existing Git repository root (including an unborn root after `git init`); creates or reuses an exact-path native Hermes Project; does not run `git init` itself.
   - Updated launch precedence: reflects exact 4-level precedence (`--project PATH`, `AETHER_PROJECT_ROOT`, verified `AETHER_PROJECT_ID`, current/nearest initialized directory); an uninitialized cwd refuses with actionable guidance rather than opening a sole registered project; updated personal shell defaults guidance.

2. **`docs/guides/project-initialization.md`**:
   - Clarified preconditions: unborn Git root accepted; exact-path native Hermes Project reused or created and verified when absent; `--hermes-project` needed only when multiple matches exist.
   - Clarified greenfield limit: owner runs `git init` first; `aether init` does not run `git init` itself, keeping Git creation explicitly owner-controlled.

3. **`docs/reference/cli.md`**:
   - `aether init` details: notes acceptance of unborn root and automatic creation/reuse of native Hermes Project.
   - Top-level `aether` launch: precedence updated to remove the sole-project fallback; uninitialized cwd fails with actionable guidance.

4. **`docs/reference/limitations-and-troubleshooting.md`**:
   - Updated greenfield initialization, native project binding, and bare project launch rows to state delivered behavior truthfully without forward-looking claims.

5. **`docs/capabilities.toml` & `docs/reference/capabilities.md`**:
   - `cli.init`: updated notes describing unborn Git root acceptance and native Hermes Project create/reuse.
   - `cli.aether-launch`: updated notes aligning with the 4-level precedence resolver.
   - Regenerated `docs/reference/capabilities.md` using `scripts/check_documentation.py --write`.

6. **`.github/workflows/policy.yml`**:
   - Applied canonical base manifest entry for `.aether/objective-contracts/oc_79b55027e7c3688d/v1.md`.

7. **`tests/test_observation_usage_guidance.py`**:
   - Updated launcher-precedence oracle to match the implemented resolver: verifies actionable init guidance for single registered project from uninitialized cwd, `ambiguous project identity` for multiple, and validates the updated guidance prose.

---

## 2. Requirement → check → observed result → evidence

| Requirement / oracle | Check command | Observed result | Evidence |
|---|---|---|---|
| Documentation validator | `uv run --frozen python scripts/check_documentation.py` | **PASS**, documentation validation passed | `scripts/check_documentation.py` |
| Launcher-precedence oracle | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_usage_guidance.py -q` | **PASS**, 9 passed in 0.32s | `tests/test_observation_usage_guidance.py` |
| Canonical base manifest | `uv run --frozen python scripts/run_tests.py -- tests/test_public_artifacts.py -q` | **PASS**, 9 passed in 2.56s | `tests/test_public_artifacts.py` |
| Static quality | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen mypy src/aether_agents` | **PASS**, clean | Direct tools |
