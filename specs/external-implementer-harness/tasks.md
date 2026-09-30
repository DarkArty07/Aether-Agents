# External Implementer harness — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_f1ea2c4a2e0662da@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_f1ea2c4a2e0662da/v1.md`
(SHA-256 `a54e75c2bf8a06285dd841cd1dd34aa603ec69235ebb3c9161da3a78e727ddb8`)
on Aether base `2221302f1c93fb4ffd166df9b5482aa2fecaef7a`.

**Owning issue:** [#563](https://github.com/DarkArty07/Aether-Agents/issues/563).

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract, `specs/external-implementer-harness/{spec,plan,research,quickstart}.md`,
or the PD-40 amendment. Card bodies remain the executable unit deliveries. The
plan's line locators are inspection notes from `4bbf8ac2`; they were re-confirmed
against this base and are not patch instructions.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Contract bytes | SHA-256 matches the envelope exactly |
| Base commit | worktree HEAD is `2221302f1c93fb4ffd166df9b5482aa2fecaef7a`, the named base, working tree clean |
| Design sufficiency | EIH-01–EIH-12, OD-1–OD-10, shared identifiers (plan §3.1), eligibility (plan §3.5), fallback triggers (plan §3.11), fail-closed rule and verification (quickstart) are decided; no missing product API |
| Proportionality | Verification matches OD-7 minimal verification plus the existing `CONTRIBUTING.md` gate; one isolated real run, no campaign. No oversized machinery to challenge |
| Profiles | `implementer` and `supervisor` exist; no extra roles created |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` is observation only; Aether Canonical procedures apply |
| Stop conditions | plan §7 assumptions (readiness event sequence, hook/MCP coexistence with the user's configuration) are verified during construction and return to Morfeo if false |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| One increment, shared interfaces | Contract field → board metadata → launcher → adapter → MCP/hook/receipt must agree on plan §3.1 identifiers | Identifiers, eligibility and fallback triggers are stamped below; units do not re-decide them |
| Default path identity (EIH-01) | No selection means identical contract bytes, identical board metadata and the exact Hermes argv/env the dispatcher would have resolved | EIH-A owns the renderer/board proof; EIH-B owns the launcher pass-through proof, including board/database read failures |
| Shared writable files | `store.py`, `hermes_plugin.py`, `pyproject.toml` and the documentation set are each owned by exactly one unit | Four implementation units; the MCP server and PD-71 adapter are concentrated in EIH-C because both are defined against the launcher's per-attempt identity and config |
| Guidance (EIH-11) | OD-1 text lives in Morfeo's SOUL and `objective-contract-design`; docs/registry/changelog are reconciled together | EIH-D owns all of it so no two units edit guidance |
| Verification | Focused tests per unit with stub `hermes`/`claude`; the integrated gate and the single real run are closeout | Implementers run only their focused tests; EIH-INT runs quickstart §2 and §3 |
| Publication | Implementer commits locally and never pushes | EIH-INT owns the R8 closeout |

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| EIH-01 (renderer/board half), EIH-02, AC1 (bytes/metadata), AC2 | EIH-A | Selection parameter, validation, rendering, projection, reuse equality, rc17 reader tolerance |
| EIH-01 (launcher half), EIH-03, AC1 (pass-through), AC3 | EIH-B | Console script, plugin `HERMES_BIN` override, eligibility routing, exact pass-through |
| EIH-04, EIH-05, EIH-06, EIH-07, EIH-08, EIH-09, EIH-10, AC4–AC8 | EIH-C | Adapter, readiness, lifecycle, fallback, receipt, worker MCP, PD-71 hook, context and skills |
| EIH-11, AC9, D2 | EIH-D | SOUL, skill, expected-behavior guide, user page, capabilities registry and generated reference, changelog |
| EIH-12, AC10, AC11, D3 | EIH-INT | Integrated gate, isolated real run, evidence, PR, issue #563, cleanup, release conclusions |

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_f1ea2c4a2e0662da@v1` plus
   `specs/external-implementer-harness/{spec,plan,research,quickstart}.md`. Skills
   grant no authority. Do not edit the canonical Objective Contract or those design
   artifacts.
2. Start from base `2221302f1c93fb4ffd166df9b5482aa2fecaef7a`. If the branch base has
   moved, rebase only with Supervisor's instruction.
3. Fixed identifiers (plan §3.1): tool parameter `implementer_harness` with enum
   `hermes | claude-code`; front-matter key `implementer_harness: "claude-code"`
   (absent means Hermes); board metadata key `aether_implementer_harness: "claude-code"`
   (absent means Hermes); console script `aether-kanban-worker`; MCP server name
   `aether-worker`; receipt schema `aether.harness-receipt.v1`; comment first line
   starts with `aether-executor:`.
4. Selection semantics (plan §3.2, §3.3): accepted only by `begin` and `supersede`;
   any other action receiving it is rejected. `begin`: omitted or `hermes` means no
   selection. `supersede`: omitted inherits, `hermes` clears, `claude-code` sets.
   The key is rendered and projected only when set. Unknown values are rejected, never
   treated as absent. Reuse requires equality including absent/absent, else the
   existing identity-conflict error.
5. Eligibility (plan §3.5) requires all of: the seven Kanban environment variables
   present and the workspace directory existing; `HERMES_PROFILE=implementer`; board
   metadata carrying an Aether contract identity and
   `aether_implementer_harness == "claude-code"`; `HERMES_KANBAN_GOAL_MODE` not `1`;
   a work claim (latest `claimed` event has no `source_status: "review"`,
   `HERMES_KANBAN_REVIEW_AFFINITY` unset, argv has no `--resume`); no `-m`,
   `--provider` or `--reasoning` in argv; a `claude` executable on `PATH`. Any failure
   or any exception resolves to the Hermes pass-through.
6. The Hermes pass-through (plan §3.5) execs `hermes` on the inherited `PATH`, else
   the interpreter's `hermes_cli.main` module form, with the unchanged argv tail and
   environment, and never re-reads `HERMES_BIN`.
7. The Claude command (plan §3.6) is exactly the listed flags. Forbidden: `--bare`,
   `--strict-mcp-config`, `--setting-sources`, `CLAUDE_CONFIG_DIR`, `--model`,
   `-w`/`--worktree`, `--continue`, `--resume`. Aether never reads, copies or stores
   Claude credentials and never modifies the user's Claude configuration.
8. Fallback triggers and non-triggers (plan §3.11) are fixed. Fallback is one `execv`
   of the same pass-through inside the same claim, PID and remaining deadline, at
   most once per attempt. A clean exit without a transition exits 76.
9. Routing uncertainty resolves to Hermes; PD-71 uncertainty resolves to block (exit 2).
   The PD-71 policy file is not modified; the hook adapter translates and calls it.
10. No new third-party runtime dependency. The standard library and the release's
    existing `mcp` extra suffice.
11. Writable-file ownership below is exclusive. Concurrent edits to the same file are
    forbidden. A needed change to a file owned by another unit returns to Supervisor.
12. Focused tests use stub `hermes` and stub `claude` executables and disposable
    roots. Never touch live boards, live Hermes homes, the runtime selector, or the
    owner's Claude configuration. Real Claude Code calls are forbidden in these units;
    only EIH-INT runs quickstart §3.
13. Unit evidence path: `specs/external-implementer-harness/evidence/<unit-id>.md`.
    No secrets, credentials, operator home paths or raw transcripts.
14. Local judgement: module and file names other than the §3.1 identifiers, internal
    structure, private test names and fixture layout. Eligibility, fallback triggers,
    the fail-closed rule, identifiers and the forbidden-flag list are not local choices.
15. Local commit on the unit branch; same-card Supervisor review; no push, PR, merge
    or issue close. Unit compatibility evidence is `minor` (additive, opt-in). The
    aggregate conclusion belongs to EIH-INT.
16. Verification while iterating: `uv run --frozen pytest <the unit's new test files> -q`
    and `git diff --check`. Record command, revision, result and evidence location.

## Execution graph

```text
t_d066909f (Supervisor decomposition root)
    → EIH-A  t_a1c42d22 contract selection and board projection   (Implementer)
    → EIH-B  t_d3197963 gateway override and launcher routing     (Implementer)
    → EIH-C  t_be9fc19e Claude adapter, worker MCP, PD-71 hook    (Implementer)
    → EIH-D  t_53f0d535 guidance and documentation                (Implementer)
    → same-card Supervisor review on each implementation unit
    → EIH-INT t_a2efd73f terminal integration/closeout            (Supervisor)
```

EIH-A, EIH-B, EIH-C and EIH-D are independent: exclusive writable files, shared
decisions already fixed, no prerequisite artifact between them. EIH-C is one
concentrated unit because the adapter, the worker MCP server and the PD-71 hook
adapter are defined against the same per-attempt identity, environment and config
files the launcher builds; splitting them would force concurrent edits to the
launcher. Same-card review is the unit review lane. EIH-INT consumes independently
reviewed units and does not replace unit review.

## EIH-A — Contract selection and board projection

- Source: EIH-01 (bytes and metadata), EIH-02, AC1 (bytes/metadata half), AC2; plan §3.2, §3.3.
- Outcome: `objective_contract` accepts optional `implementer_harness` on `begin` and
  `supersede` only. `begin` omitted/`hermes` renders bytes identical to the pre-change
  renderer and projects no metadata key; `claude-code` renders the front-matter key and
  projects `aether_implementer_harness`. `supersede` inherits, clears or sets as decided.
  Unknown values and use on other actions are rejected. Reuse validates equality,
  absent/absent included, and mismatches raise the existing identity conflict. An
  rc17-style parser accepts a selected final contract. `show` reports the selection.
- Inputs: base `2221302f`. No prerequisite unit.
- Boundaries: writable `src/aether_agents/objective_contracts/store.py`,
  `src/aether_agents/objective_contracts/hermes_plugin.py` (selection parameter, schema,
  `prepare_handoff` projection and reuse validation only), and new focused tests under
  `tests/` (for example `tests/test_implementer_harness_selection.py`). Do not edit the
  plugin's `register` function (EIH-B owns the `HERMES_BIN` override) or `pyproject.toml`.
- Judgement: private helper names and test layout.
- Verification: quickstart §1 contract-selection and board-projection bullets, including
  a byte comparison against the pre-change rendering for the unselected case.
- Dependencies: decomposition root only.
- Completion: local commit; evidence `evidence/EIH-A.md`; same-card review; no push.

## EIH-B — Gateway override and launcher routing

- Source: EIH-01 (launcher half), EIH-03, AC1 (pass-through half), AC3; plan §3.4, §3.5.
- Outcome: the package declares the `aether-kanban-worker` console script. The plugin
  sets `HERMES_BIN` only to a regular executable launcher resolved from the running
  release's own scripts directory without passing through `runtime/current`, only inside
  the Morfeo profile check, idempotently, leaving the environment unchanged otherwise.
  The launcher routes to the adapter seam only when every plan §3.5 condition holds, and
  otherwise execs the pre-change Hermes entry with identical argv and environment,
  including when the board file or database cannot be read. It never re-reads `HERMES_BIN`.
- Inputs: base `2221302f`. No prerequisite unit. The adapter entry it calls is the seam
  named in shared decision 3; EIH-C implements it.
- Boundaries: writable `pyproject.toml` (`[project.scripts]` entry only),
  `src/aether_agents/objective_contracts/hermes_plugin.py` (`register`'s `HERMES_BIN`
  override only), the new launcher module and its console-script target, and new focused
  tests (for example `tests/test_kanban_worker_launcher.py`). Do not edit `store.py` or
  the selection/projection code EIH-A owns. The launcher's Claude branch is a single
  call into the adapter seam; do not implement the adapter here.
- Judgement: launcher module path and internal function names.
- Verification: quickstart §1 plugin-override and launcher-routing bullets, using a stub
  `hermes` that records argv and environment.
- Dependencies: decomposition root only.
- Completion: local commit; evidence `evidence/EIH-B.md`; same-card review; no push.

## EIH-C — Claude adapter, readiness, worker MCP and PD-71 hook

- Source: EIH-04, EIH-05, EIH-06, EIH-07, EIH-08, EIH-09, EIH-10, AC4–AC8; plan §3.6–§3.12.
- Outcome: eligible attempts run the official `claude` binary with the plan §3.6 command
  and no forbidden flag; the work prompt is withheld until MCP, bypass and the PD-71 hook
  are proven active; the process group is empty and the single-writer check passes before
  any fallback; outcomes classify per the plan §3.11 table; fallback happens exactly once
  by `execv` within the same claim; a clean exit without a transition exits 76; SIGTERM,
  cancellation, a lost claim and a surviving writer never fall back. The per-attempt worker
  MCP server exposes exactly the derived Kanban worker set plus `project_knowledge` and
  `work_memory`, identity-bound, forwarding only supplied arguments. The PreToolUse adapter
  maps Claude payloads per plan §3.10 onto the unchanged PD-71 policy and exits 2 on every
  failure mode. Context and the per-attempt skills plugin match plan §3.8, and nothing is
  written to project or personal skill directories. Receipts and the `aether-executor:`
  comment are produced, transient inputs are removed, and no Hermes session row is created.
- Inputs: base `2221302f`. No prerequisite unit. Consume the launcher seam EIH-B calls.
- Boundaries: writable the new adapter, worker MCP server, PD-71 hook adapter and context
  builder modules under `src/aether_agents/`, plus new focused tests (for example
  `tests/test_claude_code_adapter.py`, `tests/test_worker_mcp_server.py`,
  `tests/test_pd71_claude_hook.py`). Do not modify `policy/hooks/aether_pre_tool_policy.py`,
  `store.py`, `hermes_plugin.py`, `pyproject.toml`, or any file under
  `src/aether_agents/resources/`. Do not copy `KANBAN_GUIDANCE` into Aether source; import
  it at run time.
- Judgement: module layout, the readiness mechanism within plan §3.7's invariant,
  heartbeat rate within plan §3.11, receipt path layout and equivalence-table wording.
- Verification: quickstart §1 adapter, context, worker MCP, PD-71 and receipts bullets,
  using a stub `claude` emitting canned stream-json. If no deterministic ordering keeps
  the work prompt away from the model until the hook is proven active, stop and return to
  Supervisor rather than weakening the gate (plan §7).
- Dependencies: decomposition root only.
- Completion: local commit; evidence `evidence/EIH-C.md` including the exposed MCP tool
  list; same-card review; no push. No real Claude Code call.

## EIH-D — Guidance and documentation

- Source: EIH-11, AC9, D2; plan §3.13.
- Outcome: Morfeo's SOUL and `objective-contract-design` state OD-1 (selection only on the
  owner's explicit request, Hermes otherwise, no proposal or question). The
  expected-behavior guide, the current user page, `docs/capabilities.toml` with its
  generated `docs/reference/capabilities.md`, and a `CHANGELOG.md` Unreleased entry
  describe the opt-in, the minimum requirements, fallback and limits, per `CONTRIBUTING.md`.
  Where one does not apply, record a specific non-applicability rationale.
- Inputs: base `2221302f`. No prerequisite unit.
- Boundaries: writable `src/aether_agents/resources/profiles/morfeo/SOUL.md`,
  `src/aether_agents/resources/skills/objective-contract-design/SKILL.md`,
  `docs/guides/expected-behavior.md`, the applicable current user page, `docs/capabilities.toml`,
  the generated reference, `CHANGELOG.md` (Unreleased only), and focused guidance tests if
  the repository tests guidance text. Do not edit `src/aether_agents/*.py`, `pyproject.toml`
  or `policy/`.
- Judgement: wording, provided it states OD-1 and the plan §3.13 minimum requirements
  without adding behavior.
- Verification: quickstart §1 guidance bullet; `uv run --frozen python scripts/check_documentation.py`
  and `git diff --check`.
- Dependencies: decomposition root only.
- Completion: local commit; evidence `evidence/EIH-D.md`; same-card review; no push.

## EIH-INT — Terminal integration and closeout

- Source: EIH-12, AC10, AC11, D3; quickstart §2, §3, §4; plan §8.
- Outcome: independently reviewed EIH-A through EIH-D commits integrated without
  squash, amend, rebase or force; the quickstart §2 integrated gate green; one isolated
  real Claude Code run per quickstart §3 recorded in `evidence/`; normal branch push, PR,
  required checks, green merge without bypass, issue #563 reconciliation and
  objective-owned branch/worktree cleanup. Final receipt with criterion mapping, exact
  revisions, PR/check/merge/issue state, cleanup and release conclusions
  `release_impact=minor`, `release_action=defer`, `release_channel=none`.
- Inputs: independently reviewed EIH-A, EIH-B, EIH-C and EIH-D commits plus this `tasks.md`.
- Boundaries: integration-owned wiring and conflict repairs that introduce no new
  behavior, `specs/external-implementer-harness/evidence/` and `tasks.md` status.
  Behavior gaps return as implementation rework within the review budget.
- Verification: quickstart §2 commands; quickstart §3 with disposable roots and the
  owner's already-provisioned Claude Code login; no live board, Hermes home or runtime
  selector; `git diff --check`.
- Dependencies: decomposition root and all four independently reviewed implementation units.
- Completion: merged PR and reconciled issue are success; local integration alone is not.
  Morfeo records exact-result reception afterwards.

## Authority and stop conditions

Follow the Objective Contract. Ordinary implementation, review and the R8 routine path
in `DarkArty07/Aether-Agents` are authorized. Real Claude Code calls are authorized only
inside EIH-INT for quickstart §3 and bounded event-sequence probes, in disposable scope.
Stop and return to Morfeo when a plan §7 stop condition holds: `HERMES_BIN` cannot reach
the dispatcher without a Hermes core change; PD-71 cannot be made blocking and fail-closed
with bypass active; hook activation cannot be proven before the work prompt; the worker
MCP server or hook cannot coexist with the user's configuration without managing it; a
single writer cannot be guaranteed; MCP readiness cannot be verified deterministically; or
the design would need a Hermes fork change, new credentials, Claude token handling, a
release or another out-of-scope effect. A protected-edge denial is authoritative. Unit
review is same-card. Preserve unrelated and pre-existing worktrees, branches and processes.
