# v0.20.0 Self-Improvement Instrumentation — Implementation Report

## Verdict

`MEASUREMENT SUBSTRATE IMPLEMENTED — DEFAULT OFF`

A default-off, project-scoped, privacy-preserving session ledger is implemented, independently reviewed, integrated, and released as v0.20.0. It is not activated, operationally piloted, deployed, or enabled in the release configuration.

This increment is **instrumentation, not a self-improvement cycle**. It contains no evaluator, no candidate isolation, no before/after comparison and no rollback, so no causal claim that Aether improved can be derived from it. The external logic audit (`EXTERNAL_LOGIC_AUDIT.md`) records the full reasoning; the Phase 1 corrections below make the instrumentation truthful, while Phases 2-3 — the parts that would make causality possible — remain unbuilt.

## Delivered components

- `src/olympus_v3/self_improvement/manifest.py`
  - Strict `CYCLE.yaml` loader.
  - Canonical Aether project identity checks at the nearest Git repository boundary.
  - Fail-closed provider, persistence, authorization, and next-version invariants.
- `src/olympus_v3/self_improvement/ledger.py`
  - Project-local SQLite ledger at `.aether/self_improvement.db`.
  - Exact-once sessions, tool/model measurements, Harmonia classifications, interruption state, and deterministic aggregates.
  - `0600` file creation, symlink rejection, parameterized SQL, and atomic tool/coordination observations.
- `src/olympus_v3/self_improvement/hooks.py`
  - Hermes Agent hooks for session initialization, first-turn context, tool/model measurements, turn outcome, and finalization.
  - Concurrent live sessions are preserved; only provably stale owners require reconciliation.
  - Arguments, tool results, user messages, assistant responses, and conversation history are discarded.
- `src/olympus_v3/self_improvement/evidence.py`
  - Deterministic next-version signal aggregation.
  - Atomic release-evidence projection with no model-generated prose.
- `home/plugins/aether-self-improvement/`
  - Discoverable Hermes Agent plugin wrapper and manifest.
  - Deliberately absent from `plugins.enabled`.
- `tests/test_self_improvement.py`
  - Preserved 26-case behavioral and adversarial baseline for identity, isolation, exact-once initialization, concurrency, interruption, redaction, atomicity, evidence, and default-off discovery.
- `tests/test_self_improvement_contract.py`
  - 28 audit and independent-review regressions covering real Harmonia envelopes, tool-result truth, request-scoped call identity, explicit-root isolation, lifecycle recovery, worktree baselines, schema refusal and evidence limits.

## Runtime boundaries

The plugin appears in `hermes plugins list` as:

- source: `user`
- version: `0.20.0`
- status: `not enabled`

The versioned Olympus MCP configuration excludes `talk_to`. The existing `harmonia` tool remains present but feature-disabled by configuration. No fallback was restored.

## Verification

- Self-improvement contract: `54 passed` (26 original, unmodified, plus 28 audit and independent-review regressions)
- Coordination subsystem tests: `944 passed`
- Full consolidated repository suite: `1198 passed`
- Ruff: pass
- Manifest/default-off smoke: pass
- Plugin discovery smoke: pass, not enabled

## Audit corrections applied (Phase 1)

Each entry names the finding it closes in `EXTERNAL_LOGIC_AUDIT.md`.

- **F-01** — the Harmonia classifier read `status`/`success`, fields Harmonia never emits. It now reads `error.code` and `state` against the kernel's real contract, preserves `uncertainty`, and treats anything not provably pre-admission as post-admission. Previously 0 of 9 durable states and 3 of 13 error codes classified correctly.
- **F-02** — a tool result reporting failure without an `error` key or `exit_code` was recorded as a success. The host's own `status` is now used, with a stricter local parser as fallback.
- **F-03** — `tool_call_id` was a global primary key while Hermes derives it from call content, so repeated commands silently collapsed. Independent review found that `(session_id, turn_id, tool_call_id)` still lost identical calls across model requests inside one turn. Identity is now `(session_id, turn_id, api_request_id, tool_call_id)`, preserving real retries while duplicate observer delivery remains idempotent.
- **F-06** — environment redirection and nested-repository inheritance were already rejected, but independent review found that an arbitrary explicit `project_root` kwarg could still redirect a foreign repository. The nearest active Git repository is now authoritative; an explicit root may only confirm the same discovered root.
- **F-07** — `candidate_version` is pinned to its release directory.
- **F-11** — `on_session_start` never fires on continuation, so resumed sessions recorded nothing. `post_tool_call` and `post_llm_call` now initialize lazily.
- **F-12** — `_git_head` returned `unknown` for linked worktrees, including this candidate's own. Loose refs are now resolved in the common dir.
- **F-13** — the baseline records a dirty-worktree digest, so uncommitted third-party work cannot be silently folded into a comparison.
- **F-14** — one interrupted turn latched a session into `reconciliation_required` forever. Turns are now recorded individually and session status is derived, so a session recovers while the interruption stays visible.
- **F-15** — reusing a session id under a different manifest digest or baseline is refused instead of silently merging evidence.
- **F-16** — the ledger carries a schema version and refuses an incompatible file loudly. Previously an older schema produced a healthy-looking session with zero evidence.
- **F-19** — the manifest digest is re-verified at finalization and drift is recorded.
- **F-23** — exact-checkout verification reproduced the intermittent concurrent reconciliation failure. `dispatch.unknown` is internally integrity-signed and is now verified as an internal ledger event during replay; a deterministic regression covers the path.
- **F-24** — the evidence projection now states what it cannot establish and surfaces baseline and drift integrity.

Deliberately **not** applied: the F-08 `authorization` redesign, because it would require rewriting an existing acceptance test. Only its silent-failure half was fixed. See `BENCHMARK_REPORT.md`.

## Remaining gates

The following remain intentionally open or blocked:

- live plugin activation;
- runtime restart;
- live Aether session observation;
- bounded Harmonia pilot;
- causal before/after acceptance;
- coordination key creation;
- deployment and production activation/publication.

The next minor architecture remains undecided pending operational evidence and product-owner approval.
