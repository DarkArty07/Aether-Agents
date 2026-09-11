# 006 — Execution breakdown (Supervisor-owned)

Supervisor receipt review and decomposition for Objective Contract
`oc_6176d2be6cb7e6fe@v1` (`.aether/objective-contracts/oc_6176d2be6cb7e6fe/v1.md`,
SHA-256 `69765e73e657b7c0854454a4257a43e5f113ed9c4deb9c6559c536b374a5c040`).
This is a derived execution breakdown: it maps contract requirements to units and
cannot widen scope, authority or acceptance. Canonical owners remain `spec.md`,
`plan.md`, `research.md`, `quickstart.md` and `evidence.md`; native card ids,
worktrees, branches and role selections are board side data, not portable content.

## Receipt verification (completed before fan-out)

| Check | Result |
|---|---|
| Project binding (`.aether/project.toml`) | `12027989-a08f-41cd-a82c-54ff1bfb6b03` — matches contract |
| Contract digest (working tree and base-commit blob) | `69765e73…374a5c040` — matches the envelope |
| Base commit | `3ce47369165dda9c7df3452730c8caf1ee0a6ca0`; worktree HEAD equals it and the tree is clean |
| Canonical owners present at base | `spec.md`, `plan.md`, `research.md`, `quickstart.md`, `evidence.md`, `fixtures/binding_privacy_probe.py` |

The first dispatch of this root was provisioned on an unrelated checkout and was
recovered natively (HLP-354) before this verification. No unit was created against
the superseded tree, and no unit may consume it.

## Verified inputs

| Source | Revision | Role |
|---|---|---|
| Aether execution base | `3ce47369165dda9c7df3452730c8caf1ee0a6ca0` | every Aether unit branch starts here |
| Maintained fork repair source (`DarkArty07/aether-hermes`) | `266e412fb83ad32af92ed391db942f88993d76a2` (= `origin/aether-main`) | fork units branch from this full revision; the checkout's local `aether-main` label is stale |
| Public qualification baseline | `e624e9fde561e1add9388384012b295fde669ade` | unchanged; no release-lock migration is in scope |
| Live editable runtime | resolved at unit time by independent file hashes | inspection only; adoption is terminal-card work |

## Requirement coverage

| Requirement | Unit(s) | Acceptance oracle |
|---|---|---|
| TS-373 | U373 | Exact-session explicit binding resolves when native cwd is absent, empty or an ordinary existing non-Git directory; conflict/identity/marker/unregistered/unreadable negatives still fail closed; real graph and memory resolution plus isolated save/read |
| TS-390 | U390 | Schema-valid `stop`, `tool_calls` and `error` histograms survive capture → reduce → storage → compact query with original counts; raw/wrong-namespace payloads remain rejected |
| TS-389 | U389 | The original harmless Python log-read path is accepted while direct lifecycle commands and referenced real shell scripts stay detected; malformed/ambiguous forms stay conservative |
| TS-382 | U382R → U382F | Bounded causal qualification, then a persistence-safe writer repair with atomic transcript, tail, counters, ownership and rollback intact — no timeout inflation or dropped writes |
| TS-275 | U275R → U275F | Bounded real-route qualification, then a real invocation that interprets image-only content through the provisioned route, not a loopback or forced-route substitute |
| TS-P | all units + terminal | Scope diff, isolated fixtures, preserved unrelated state, residue audit |
| TS-C | terminal | Independent unit review, exact integrated revisions, required checks, authorized PR/merge, per-issue runtime receipts |

## Units

| Unit | Requirement | Assignee | Outcome | Writable surface | Verification | Depends on |
|---|---|---|---|---|---|---|
| U373 | TS-373 | implementer | Native-evidence classification before binding precedence, so an ordinary non-Git cwd falls through to the exact-session explicit binding | `src/aether_agents/knowledge/bindings.py`, `knowledge/context.py`, `knowledge/common.py` only if the code contract requires it, the native knowledge plugin boundary where required, `tests/test_knowledge_plugin_cli.py` (+ new focused module), `specs/006-tools-memory-stability/evidence/TS-373.md` | Probe fixture TS-373 cases; knowledge plugin suite; deterministic positive/negative matrix incl. subdirectory and attached worktree; isolated work-memory save/read | Root |
| U390 | TS-390 | implementer | Namespace- and type-aware validation of the schema-owned finish-reason histogram through the real observation pipeline | `src/aether_agents/observation/capture/projectors.py`, `observation/reduce/reducer.py`, `observation/privacy.py`, `observation/storage.py`, `observation/query.py`, `observation/contracts.py` (shared typed validator if the module permits), affected `tests/test_observation_*.py`, `specs/006-tools-memory-stability/evidence/TS-390.md` | Probe fixture TS-390 cases; contracts/reducer/journal-storage/brief suites; EventBuilder → persistence → reduce → ReadModel → compact query traversal | Root |
| U389 | TS-389 | implementer | Syntax-aware referenced-script view for well-formed quoted Python heredocs without weakening direct lifecycle detection | Fork: `cron/lifecycle_guard.py`, `tools/shell_heredoc.py`, `tools/terminal_tool.py` where required, `tests/tools/test_terminal_heredoc_background_guard.py`, `tests/tools/test_self_repo_guard.py`, `tests/hermes_cli/test_gateway_restart_loop.py` (+ new focused module). Aether side: `specs/006-tools-memory-stability/evidence/TS-389.md` | Causal RED → GREEN on the harmless log-read path; full guard/control matrix incl. real direct/referenced lifecycle controls never executed; fork focused suites; source-hash parity vs the live runtime | Root |
| U382R | TS-382 (research) | implementer | Causal proposal and pre/post oracle for transcript-write starvation, or a precise access blocker | `specs/006-tools-memory-stability/evidence/TS-382-research.md` (+ deterministic reproduction fixture under `specs/006-tools-memory-stability/fixtures/` if it stays read-only against live state) | Real SessionDB paths in a temporary DB; deterministic writer/append overlap; sanitized timing metadata; no live DB mutation | Root |
| U275R | TS-275 (research) | implementer | Real-route qualification of image interpretation plus causal boundary and pre/post oracle, or an exact capability blocker | `specs/006-tools-memory-stability/evidence/TS-275-research.md` | One bounded real invocation through the already provisioned tool/client with image-only content; protocol/API schema checked before blaming a backend; no blind retries | Root |
| U382F | TS-382 (repair) | implementer | Persistence-safe writer repair implementing the Morfeo-recorded design | Fork paths named by the recorded design revision (expected `hermes_state.py` and adjacent state modules, `tests/state/*`). Aether side: `specs/006-tools-memory-stability/evidence/TS-382.md` | Pre-fix failure reproduced by the research oracle then preserved persistence post-fix: atomic visible transcript replacement, concurrent append/tail, counters, ownership, rollback | Root, U382R, Morfeo design checkpoint |
| U275F | TS-275 (repair) | implementer | Minimal compatible image-route repair implementing the Morfeo-recorded design | Fork paths named by the recorded design revision (expected `tools/vision_tools.py`, `agent/image_routing.py`, `agent/codex_responses_adapter.py`, `agent/transports/codex.py` and their suites). Aether side: `specs/006-tools-memory-stability/evidence/TS-275.md` | Real provisioned route interprets image-only content with the route explicitly evidenced; bytes, tool-call identity and chronology preserved; protocol-scoped normalization | Root, U275R, Morfeo design checkpoint |
| UINT | TS-P, TS-C (terminal) | supervisor | Integrated, independently verified result: retained reviewed commits, full gates, scoped runtime adoption, per-issue receipts, authorized GitHub closeout and residue audit | Integration-owned artifacts only: canonical stage records (`evidence.md`, `research.md` consolidation, `HERMES_LOCAL_PATCHES.md`, patch accounting) on the integration branch | Declared full checks in both repositories, reviewed-unit consumption, scoped runtime canary with rollback evidence, per-issue acceptance receipts | Root, U373, U390, U389, U382F, U275F |

`U382F` and `U275F` are deliberately not build-qualified. `plan.md` states their exact
algorithm is not declared build-ready until the causal gate proves it. Their bodies
therefore carry a precondition: if the recorded Morfeo design for the requirement is
absent when they start, the unit blocks through the native revision signal instead of
inventing a repair.

## Dependency reasons

- Every unit depends on the verified decomposition root: the earlier provisioning
  defect would otherwise have given children a foreign base.
- `U382F` → `U382R` and `U275F` → `U275R`: the repair premise (which writer, which
  transport boundary) does not exist yet; `spec.md` requires the material premise to
  return to Morfeo before either repair is built.
- `UINT` → root and all implementation units: terminal integration consumes reviewed
  units and cannot substitute for same-card unit review.
- No false edges: TS-373, TS-390, TS-389 and the two research gates touch disjoint
  surfaces and are dispatched together; consecutive numbering above is not an order.

## Shared writable files (Supervisor decision)

Canonical stage records have exactly one writer. `spec.md`, `plan.md`, `research.md`,
`quickstart.md`, `evidence.md` and `HERMES_LOCAL_PATCHES.md` are Morfeo- or
terminal-owned; units never edit them. Each unit records attributed evidence in its
own file under `specs/006-tools-memory-stability/evidence/`, and the terminal card
consolidates the per-requirement records into `evidence.md` and the research record
into `research.md`, including the ready-to-consolidate patch ledger entry each fork
unit writes into its own evidence file. This avoids two units writing one file while
preserving every required record.

No two units share a writable code file: the Aether units own disjoint packages
(`knowledge/` and `observation/`), and the fork units own disjoint surfaces
(guard/heredoc, state writer, vision/adapter). If a unit discovers it must change a
file owned by another unit, it stops and reports the collision rather than editing it.

## Parallelism and queueing

Immediately runnable after the root: `U373`, `U390`, `U389`, `U382R`, `U275R`. They are
genuinely independent, so they are released without artificial ordering; the
implementer profile's configured concurrency means some queue behind others, and queue
wait is recorded as such rather than as a dependency. `U382F` and `U275F` are
serialized behind their research gates by material design, not convenience. `UINT`
runs last.

## Non-build obligations

- TS-P preservation: all units use isolated homes, databases, boards and worktrees;
  live SessionDB, live boards and unrelated dirty runtime state are read-only at most;
  dangerous guard strings are analysed, never executed.
- Authority: commits are local. Branch push, pull request, checks and merge belong to
  the terminal Supervisor card; no unit pushes or publishes.
- Privacy: private routing, model, endpoint, board, session and payload evidence stays
  in native card metadata or the private evidence location; it is never committed.
- Release: no package publication, deployment or release-lock migration is in scope.
  Compatibility, release action and channel remain separate terminal conclusions.

## Handoff

The root ends at this verified breakdown. Descendant cards own implementation, review
and terminal closeout through the native lifecycle; each unit requests same-card
review from the supervisor profile and the terminal card consumes only independently
reviewed units. A material design decision discovered by either research gate returns
to Morfeo through the native revision path; it is not resolved by a worker vote or by
layer-by-layer patching.
