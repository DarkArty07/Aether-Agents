# Implementation Evidence — Unit PR8-CONTRACT (#388 Fail-Closed Boundary)

**Status:** Aether-side fail-closed boundary for `#388` implemented and verified at the causal minimum (rework unit `PR8-CONTRACT-REWORK-1`). Native Hermes authoring sessions that cannot resolve a valid registered Git workspace fail closed before store construction with stable error `AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED` and zero primary checkout mutation. For resolved workspaces, positive workspace validation is delegated directly to `ObjectiveContractStore._project` without duplicate logic in the plugin. Direct sessionless store use remains completely preserved. Ready for independent Supervisor re-review on child card `t_d760638b` (`PR8-CONTRACT-REVIEW`).

**Unit ID:** `PR8-CONTRACT` (rework `PR8-CONTRACT-REWORK-1`, card `t_139b1878`)
**Parent Task ID:** `t_3250f19c`
**Objective Contract:** `oc_c780a10d94b78d85@v1` (SHA-256 `0fdd7931cc77e75eecc20e37c32f1352afbd8bf91869340aa092ac20e12905a5`)
**Source Requirements:** `specs/pragmatic-reliability-eight/spec.md` §R388; `plan.md` §D3 U-CONTRACT; `specs/pragmatic-reliability-eight/tasks.md` (PR8-CONTRACT); Issue [#388](https://github.com/DarkArty07/Aether-Agents/issues/388).

---

## 1. Repositories and Revisions

- **Aether Worktree Root:** project-linked worktree for card `t_3250f19c` (machine path omitted from public evidence)
- **Aether Branch:** `aether-agents-2/t_3250f19c-pr8-contract-objective_contract-fails-cl`
- **Aether Base Commit:** `0a41438a13a0655b07703910b605e595f55aa660`
- **Pre-mutation Target File SHA-256 (verified before mutation):**
  - `src/aether_agents/objective_contracts/hermes_plugin.py`: `6e803f59f8b2e0fb2b74b85e51a8ec8776b6e44c18821f820e16dc1dbc53e130`
  - `tests/test_objective_contracts.py`: `e0535dfa951659e0ed098d5f5bf0a5bff52e178fef9644cdb932e765cc32d5f1`
  - `src/aether_agents/objective_contracts/store.py`: `7d4473547c35ff142afd613d6ed4c98c9c785c22341d56a005d4ba97cf8e9d30` (preserved without edits)
  - `src/aether_agents/objective_contracts/execution_boards.py`: `bb9c51cfe2812ae63fde5f6c1d79543d9bb23fb5d7d58b8b2855a8949dbb6bdc` (preserved without edits)

---

## 2. Scope and Modification Boundaries

Exclusive writable boundary for PR8-CONTRACT / PR8-CONTRACT-REWORK-1:
- `src/aether_agents/objective_contracts/hermes_plugin.py`
- `tests/test_objective_contracts.py`
- `specs/pragmatic-reliability-eight/evidence/PR8-contract.md`

Preserved without edits (out of bounds for this unit):
- `src/aether_agents/objective_contracts/store.py`: preserved (zero edits; store boundary unchanged, preserving direct sessionless use).
- `src/aether_agents/objective_contracts/execution_boards.py`: preserved.
- `HERMES_LOCAL_PATCHES.md` and `patches/hermes/**`: preserved (`PR8-LEDGER` boundary).
- `.github/workflows/policy.yml` and historical contracts: preserved (`PR8-CI` boundary).
- Fork repositories and sources: preserved (`PR8-CRON` / `PR8-REVIEW` boundary).
- No push, PR creation, branch merge, issue mutation, package publication, or live activation.

---

## 3. Investigation and Defect Mechanism

### 3.1 Defect Mechanism (Reproduced on Unchanged Baseline `0a41438a`)
In `src/aether_agents/objective_contracts/hermes_plugin.py`:
1. `_native_session_workspace(session_id: str)` inspects the native session table in `state.db`. When the session row is missing, the `cwd` is `NULL`, empty, nonexistent, or points to a non-Git directory, `_native_session_workspace` returns `None`.
2. Prior to this fix, `_handle` unconditionally passed `authoring_root=session_workspace` into `ObjectiveContractStore(...)`. When `session_workspace` was `None`, the store fell back to `self.authoring_root is None or self.authoring_root == resolved` in `store._project()`, defaulting to the primary registered Project checkout.
3. Consequently, in incident #388, an unbound or improperly initialized native session (e.g. cron without persisted workdir) authoring a contract landed draft and final writes directly into the occupied primary repository checkout rather than failing closed.

### 3.2 Fail-First Reproduction (RED on `0a41438a`)
When running `test_objective_contract_fails_closed_without_resolved_git_workspace` against the unpatched base:
```text
FAILED tests/test_objective_contracts.py::test_objective_contract_fails_closed_without_resolved_git_workspace
AssertionError: Expected failure for negative: missing session row, got: {'project_id': '11111111-1111-4111-8111-111111111111', 'contract_id': 'oc_908d6ef5b8752c2c', 'revision': 1, 'status': 'draft', 'draft_path': '.aether/drafts/oc_908d6ef5b8752c2c.json', 'created_in_session': 'session-missing-row'}
```
The negative test confirmed that an unbound session mutated the primary project checkout and created `.aether/drafts/` instead of failing closed before mutation.

### 3.3 Implementation Details (Causal Minimum on Candidate)
1. **Fail-Closed Seam Before Store Construction:** In `src/aether_agents/objective_contracts/hermes_plugin.py`, within `_handle`:
   - When `session_id` is provided and non-empty, `session_workspace = _native_session_workspace(session_id)`.
   - If `session_workspace is None` (session row missing, `cwd` is `NULL`, empty, nonexistent, or non-Git), `_handle` immediately raises `ContractError("AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED", "Hermes authoring session has no resolved Git workspace")`.
   - This check runs **before** `ObjectiveContractStore(author_profile=author_profile, authoring_root=session_workspace)` is constructed, failing closed with zero filesystem writes.
2. **Delegation of Positive Workspace Validation:**
   - When `session_workspace` is resolved (non-`None`), it is passed directly as `authoring_root` to `ObjectiveContractStore`.
   - `ObjectiveContractStore._project` enforces all registered project root, worktree, marker validity, Git-root and git common-dir constraints on every store action before any mutation.
   - The plugin does not duplicate store validation logic or construct its own separate registry.
3. **Preservation of Direct Store Use:**
   - Direct sessionless store use (or tool invocation without `session_id`) passes `authoring_root=None` as default, preserving primary root authoring for authorized callers.

---

## 4. Verification Evidence

### 4.1 Required Fixtures and Observed Results

| Fixture | Scenario Description | Check Executed | Observed Result | Evidence Location |
|---|---|---|---|---|
| Negative 1 | Missing session row in `state.db` | `hermes_plugin._handle(action="begin", session_id="session-missing-row")` | `AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED`; zero primary/draft/final mutations | `tests/test_objective_contracts.py:2567-2571` |
| Negative 2 | `NULL` cwd in `sessions` table | `hermes_plugin._handle(action="begin", session_id="session-null-cwd")` | `AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED`; zero primary/draft/final mutations | `tests/test_objective_contracts.py:2572-2576` |
| Negative 3 | Empty string `""` cwd in `sessions` table | `hermes_plugin._handle(action="begin", session_id="session-empty-cwd")` | `AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED`; zero primary/draft/final mutations | `tests/test_objective_contracts.py:2577-2581` |
| Negative 4 | Nonexistent directory cwd | `hermes_plugin._handle(action="begin", session_id="session-nonexistent-cwd")` | `AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED`; zero primary/draft/final mutations | `tests/test_objective_contracts.py:2582-2586` |
| Negative 5 | Existing non-Git directory cwd | `hermes_plugin._handle(action="begin", session_id="session-non-git-cwd")` | `AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED`; zero primary/draft/final mutations | `tests/test_objective_contracts.py:2587-2591` |
| Negative 6 | Unrelated Git repository / worktree | `hermes_plugin._handle(action="begin", session_id="session-unrelated-repo")` | `AETHER-OBJECTIVE-CONTRACT-PROJECT-MARKER-INVALID` (from store delegation); zero primary/draft/final mutations | `tests/test_objective_contracts.py:2592-2596` |
| Positive 7 | Valid linked worktree | `hermes_plugin._handle` for `begin`, `set_section`, `finalize` in `session-valid-worktree` | PASS; contract `v1.md` created in worktree; primary checkout remains 100% byte/stat/inode unchanged | `tests/test_objective_contracts.py:2676-2727` |
| Regression | Direct sessionless store use | `ObjectiveContractStore(registry=registry).begin(...)` | PASS; direct store use succeeds without session workspace constraint | `tests/test_objective_contracts.py:2668-2675` |

### 4.2 Verification Commands and Exit Codes

1. **Focused regression suite with new and updated nodes:**
   ```bash
   PYTHONPATH="$HOME/.cache/aether-agents/hermes/v2026.8.18" uv run --frozen pytest -q tests/test_objective_contracts.py
   # Result: 45 passed in 30.17s, exit code 0
   ```
2. **Linter:**
   ```bash
   uv run --frozen ruff check src/aether_agents/objective_contracts/hermes_plugin.py tests/test_objective_contracts.py
   # Result: All checks passed!, exit code 0
   ```
3. **Formatter:**
   ```bash
   uv run --frozen ruff format --check src/aether_agents/objective_contracts/hermes_plugin.py tests/test_objective_contracts.py
   # Result: 2 files already formatted, exit code 0
   ```
4. **Type checker:**
   ```bash
   uv run --frozen mypy src/aether_agents
   # Result: Success: no issues found in 53 source files, exit code 0
   ```
5. **Documentation validator:**
   ```bash
   python3 scripts/check_documentation.py
   # Result: documentation validation passed, exit code 0
   ```
6. **Public artifact scanner:**
   ```bash
   python3 scripts/check_public_artifacts.py
   # Result: Expected known historical oc_0084270d940c98d9/v1.md findings (owned by PR8-CI); zero findings from touched unit files.
   ```

---

## 5. Compatibility and Release Assessment

- **Unit compatibility impact:** `patch` (backward-compatible defect fix). Prevents unauthorized authoring writes to primary checkouts from unbound or invalid native sessions while preserving direct sessionless `ObjectiveContractStore` use and valid worktree authoring.
- **Release conclusion:** Defer to terminal Supervisor integration (`PR8-INT`). Expected aggregate: `release_impact=patch`, `release_action=defer`, `release_channel=none`.
- **Remaining risk:** Low; covered by exhaustive negative fixtures (missing row, NULL, empty, nonexistent, non-Git, unrelated repo) asserting zero mutation, positive worktree verification, and direct sessionless store regression tests.
