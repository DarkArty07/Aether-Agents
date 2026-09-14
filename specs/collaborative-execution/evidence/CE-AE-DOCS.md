# Unit Evidence: CE-AE-DOCS — normative docs, #317 disposition, canonical manifest

**Unit ID:** CE-AE-DOCS
**Objective Contract:** `oc_a28ff9b7fa20d29d@v1`
**Contract SHA-256:** `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`
**Base Commit:** `183bd7a4944a5db7d22091c402a74383a80100fa`
**Task ID:** `t_e890e56a`
**Assignee:** `implementer`
**Owning Issue:** [#334](https://github.com/DarkArty07/Aether-Agents/issues/334); related dispositions [#317](https://github.com/DarkArty07/Aether-Agents/issues/317) and [#407](https://github.com/DarkArty07/Aether-Agents/issues/407)

---

## 1. Stamped Shared Decisions (from `tasks.md`)

1. **Authority:** Objective Contract `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`). Skills grant no authority. The canonical Objective Contract is not edited.
2. **Repository & Workspace:** Aether base is `183bd7a4944a5db7d22091c402a74383a80100fa`. Fork product edits start from isolated nested worktrees of `DarkArty07/aether-hermes` at `3b81e9d91cc3a0662b910726a44c94ed328b1e90`. CE-AE-DOCS modifies only Aether repository documentation, specifications, workflows, and tests within its declared boundaries.
3. **Target File Hashes / Pre-mutation Check:** Production and normative target files verified against base `183bd7a4944a5db7d22091c402a74383a80100fa`.
4. **Signatures Preserved:** Native tool signatures and comment writers preserved.
5. **Shared Consume Interface:** Preserved and documented; internal collaboration vs owner-facing notification distinguished.
6. **Proactive Notices:** Internal collaboration advisories distinguish internal design-steward delivery from owner notifications.
7. **Stale / End-of-Flow:** Decomposition root `done` is not terminal flow completion.
8. **Surface Exclusions:** No modification to Graphify, lockfiles, live profiles, credentials, providers, models, settings, dispatcher configuration, or GitHub Actions except the single `.github/workflows/policy.yml` manifest line.
9. **Testing Standard:** Tested using project-provisioned tools (`uv run --frozen pytest`, `python scripts/check_documentation.py`, shell manifest diff emulation). No live paid model or live board.
10. **Exclusive Writable Ownership:** CE-AE-DOCS touches only its assigned normative docs, specs, workflows, and tests; no overlap with CE-AE-RES or fork units.
11. **Ledgers:** `HERMES_LOCAL_PATCHES.md` and `AETHER_FORK.md` are preserved and not modified by this unit.
12. **Evidence Path:** Unique unit evidence file at `specs/collaborative-execution/evidence/CE-AE-DOCS.md`.
13. **Local Judgement:** Applied locally for exact wording reconciliations while preserving all contract obligations and convergence phrases.
14. **Escalations:** None required; boundaries and requirements were fully specified.
15. **Handoff & Review:** Local git commit; same-card Supervisor review (`reviewer=supervisor`); unit compatibility `minor`; no push/PR/merge/issue close.
16. **Bootstrap:** Uses existing runtime baseline; does not require new runtime arguments to execute.
17. **Issue Closeout:** No GitHub issues closed from this implementation unit.

---

## 2. Starting Point and Boundary Verification

- **Workspace:** worktree @ `.worktrees/t_e890e56a` (kind: `worktree`, task ID: `t_e890e56a`)
- **Branch:** `aether-agents-2/t_e890e56a-ce-ae-docs-normative-docs-317-dispositio`
- **Clean base:** verified clean working tree at base `183bd7a4944a5db7d22091c402a74383a80100fa`.
- **Pre-check of exclusions:**
  - `src/aether_agents/resources/profiles/*/SOUL.md`: preserved (CE-AE-RES).
  - `src/aether_agents/resources/skills/*/SKILL.md`: preserved (CE-AE-RES).
  - `tests/test_contract_quality_documents.py`: preserved (FR-736b phrases untouched).
  - `HERMES_LOCAL_PATCHES.md`: preserved (CE-INT).
  - Fork files: none touched.

---

## 3. Changes Implemented

### A. Canonical Base Manifest & Workflow (`.github/workflows/policy.yml` & `tests/test_documentation.py`)
- Added `.aether/objective-contracts/oc_a28ff9b7fa20d29d/v1.md` in literal sorted position to `.github/workflows/policy.yml`.
- Validated literal sorting between `oc_924b2054e774ca5b/v1.md` and `oc_a578f1815b1eeee9/v1.md`.
- Added assertion for `.aether/objective-contracts/oc_a28ff9b7fa20d29d/v1.md` in `tests/test_documentation.py` (`test_policy_workflow_admits_the_documentation_inventory_and_runs_the_checker`).

### B. Capability Traceability (`docs/capabilities.toml` & `docs/reference/capabilities.md`)
- Updated `docs/capabilities.toml` for `skills.aether-canonical-resources` to reflect that the open-ended observation requirement in issue #317 was closed at owner direction without claiming organic PASS, and that knowledge-skill packaging does not establish live-agent adoption.
- Re-rendered `docs/reference/capabilities.md` using `python scripts/check_documentation.py --write`.

### C. Normative Design & Execution Guides (`DESIGN.md`, `AGENTS.md`, `docs/guides/execution.md`)
- `DESIGN.md`:
  - §10.1 (line 222): Clarified that instruction/resource tests are not proof of agent compliance; the open-ended observation requirement in #317 was closed at owner direction without claiming organic PASS, and unverified behavioral limits remain explicit.
  - §11 PD-77 (line 370): Reconciled PD-77 to distinguish internal Morfeo collaboration from owner-facing notifications: ordinary internal milestones stay silent to the origin as owner-facing notifications; explicit peer questions and coalesced evidence notices may reach the originating design steward without notifying the human owner. Only explicit `input`, `revision`, or `flow_terminal` routing returns to the owner-facing session.
- `AGENTS.md`:
  - Reconciled contract/execution procedure adoption: adoption was tracked in issue #317 and the execution guide; its open-ended observation requirement was closed at owner direction without claiming organic PASS. Historical evidence and unverified-behavior limits remain explicit.
- `docs/guides/execution.md`:
  - §Session affinity: Updated to distinguish internal collaboration notices reaching the design steward from owner-facing notifications (which remain silent for ordinary internal milestones).
  - §Contract/execution procedure adoption: Updated to record owner-directed closure of the open-ended observation requirement in #317 without claiming organic PASS.

### D. Specifications (`specs/r7-supervision-and-convergence/spec.md`, `specs/r6-protocol-and-communication/spec.md`, `specs/r2-contract-and-handoff/spec.md`, `specs/006-contract-execution-quality/spec.md`, `plan.md`, `quickstart.md`)
- `specs/r7-supervision-and-convergence/spec.md`: Reconciled FR-714e to state that ordinary decomposition, implementation, review and rework milestones remain silent to the origin as owner-facing notifications, while explicit peer questions and coalesced evidence notices may reach the originating design steward without notifying the human owner. Preserved all FR-736b convergence phrases.
- `specs/r6-protocol-and-communication/spec.md`: Reconciled FR-617a and FR-619 to clarify that explicit peer questions and coalesced evidence notices reach Morfeo as internal collaboration without generating owner notifications.
- `specs/r2-contract-and-handoff/spec.md`: Updated stage status and owner refinement to reflect that open-ended observation under #317 was closed at owner direction without claiming organic PASS.
- `specs/006-contract-execution-quality/spec.md`: Updated status, §Current owner decision, CQ-08, acceptance matrix, and definition of completion to record owner-directed closure of the open-ended observation gate under #317 without claiming organic PASS.
- `specs/006-contract-execution-quality/plan.md`: Updated status, D6, and D8 regarding #317 observation requirement closure.
- `specs/006-contract-execution-quality/quickstart.md`: Updated §2 and §3 to state that the open-ended observation requirement in #317 was closed at owner direction without claiming organic PASS.

---

## 4. Non-Applicability Determinations

Per task instructions and local judgement:
- `docs/roles-and-authority.md`: Inspected. It does not state the affected terminal-only rule (only standard pipeline terminal release closure via PR merge); no edit required.
- `specs/r1-foundation-and-roles/spec.md`: Directory does not exist; inspected `specs/r1-authority-and-interaction/spec.md`. It contains no matching terminal-only origin routing sentence or #317 gate sentence; no edit required.

---

## 5. Verification Results

| Check | Command / Action | Result | Evidence |
|---|---|---|---|
| Documentation & Contract Quality Tests | `uv run --frozen pytest -q tests/test_documentation.py tests/test_contract_quality_documents.py` | PASS (27 passed, 1 skipped) | Verified documentation checker, policy admittance, and preserved FR-736b strings |
| Documentation Checker CLI | `uv run --frozen python scripts/check_documentation.py` | PASS (`documentation validation passed`) | `docs/capabilities.toml` and `docs/reference/capabilities.md` in exact agreement |
| Policy Base Manifest Exact Emulation | Emulated `.github/workflows/policy.yml` lines 35–435 | PASS (0 diff) | Literal list matches `git ls-files \| grep -v '^specs/'` exactly |
| Spec Manifest Policy Emulation | Emulated `.github/workflows/policy.yml` lines 436–465 | PASS | Validated 100644 mode and portable spec paths |
| Public Artifact Path Scan | `uv run --frozen python scripts/check_public_artifacts.py` | PASS (`public artifact path scan passed: tracked surface + 0 artifact(s)`) | No operator machine paths in tracked public surface |
| Public Artifact Path Tests | `uv run --frozen pytest -q tests/test_public_artifacts.py` | PASS (8 passed) | Scanner tests pass with zero findings on tracked surface |
| Git Whitespace Check | `git diff --check` | PASS (clean, 0 output) | No whitespace or formatting errors |
| Organic PASS Assertion Audit | `git diff \| grep -i "pass"` inspection | PASS | Every #317 disposition explicitly disclaims organic PASS (`without claiming organic PASS`) |

---

## 6. Compatibility & Handoff

- **Unit Compatibility Impact:** `minor` (backward-compatible normative clarifications and additive canonical base manifest entry for `oc_a28ff9b7fa20d29d/v1.md`).
- **Release Action:** `defer` (integrated aggregate owned by CE-INT).
- **Release Channel:** `none`.
- **Review Lane:** Same-card Supervisor review requested via `kanban_request_review(reviewer="supervisor")`.
