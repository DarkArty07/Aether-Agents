# Limitations and troubleshooting

This page records current limits plainly. It does not turn a candidate interface, package source file, or historical qualification artifact into a release/readiness claim.

## Current limits

| Area | Current limit | Safe response |
| --- | --- | --- |
| Greenfield initialization | `aether init` requires an existing Git repository root (including an unborn root before the first commit); it does not run `git init`. | Run `git init` first; `aether init` reuses or creates the exact-path native Hermes Project. |
| Native Project binding | `init` reuses one exact `primary_path` match or creates one when absent; multiple matches require `--hermes-project ID`. | Pass `--hermes-project` only when multiple exact matches exist. |
| Bare project launch | Project selection is exact and verified (explicit `--project` or `AETHER_PROJECT_ROOT`, then a verified `AETHER_PROJECT_ID`, then the current/nearest initialized directory; an uninitialized directory never opens an unrelated project); installed project-aware launch is verified in isolated fixtures but not yet qualified against a live installation. | Use `--help`, `--version`, `--project PATH --json`, and `doctor` for discovery; do not infer a release-ready TUI path, and do not substitute a project name or the most recent session for an exact project identity. |
| Project-aware doctor | `doctor --project` is accepted but the full project mapping diagnosis is unfinished. | Treat result as lifecycle coherence evidence only. |
| Service lifecycle | `start`, `stop`, `restart`, and `status` return explicit unsupported results. | Do not expect this build to activate or control a service. |
| Reconciliation | `reconcile --to active` repairs the projections and selector of the already active, authenticated release only; `--to installed` and a missing `--to` return explicit unsupported, and an unauthenticated legacy active release is refused before mutation. | Use it only for the active release; a package-manager mismatch still requires `aether update` or `aether rollback`, never a record edit. |
| Observation contention | Under concurrent writers, `observe` returns the bounded retryable `STATE_BUSY` (maintenance lock held) or `CATCHUP_INCOMPLETE` (ingestion budget ended first); native `aether_observe` reports `AETHER-OBSERVE-BUSY`/`AETHER-OBSERVE-CATCHUP-INCOMPLETE`. | Retry after the contending writer or the next ingestion pass; a settled snapshot succeeds, and genuine unreadable/schema/privacy failures remain `STATE_UNREADABLE` rather than being retried as transient. |
| Guided/declarative setup | Only a local wheel/check-out/release-lock candidate interface exists. | Do not treat it as a clean public installation wizard. |
| Managed Hermes source | The executable source is the maintained fork under release-lock `schema_version` 4 source mode `maintained_fork`; the retired `transitional_fork` mode is refused and `.patch` files are never replayed. | Read the release lock for the exact repository, commit, source-tree digest and artifacts; never repair a runtime by applying a patch file. |
| Release-candidate scope | Source `1.0.0rc8` / display `1.0.0-rc.8` defines a local-only final candidate containing #495 Morfeo resources and the #497 updater repair; RC7 is the compatibility bridge with RC6-owned resource bytes. Source or local tags do not prove activation or agent behavior. Earlier tags remain immutable and published rc.1 remains rejected. This is not stable `1.0.0`, a package-index publication or WSL2 qualification. | Verify exact RC6→RC7→RC8 and rollback in disposable roots, then use `aether doctor` and the managed cutover receipt for live state; never infer activation from source, push tags or activate rc.1. Keep #261 open. |
| State export | `uninstall --export` returns `EXPORT_NOT_IMPLEMENTED`. | Preserve state; do not claim an export occurred. |
| Portable profiles | Resources are versioned candidate bytes, not proof of live profile activation. | Avoid copying private profile state into project artifacts. |
| Optional Graphify | Structural graphs are committed-revision snapshots; configured semantic maintenance is opt-in (`semantic.enabled` plus a bound auxiliary task), bounded to one 300-second update, and dirty files are not indexed. Its semantics are an additive `origin=llm` overlay, and a snapshot without the current integrity identity is reported as untrusted structural state rather than a trusted semantic result. | Check revision/coverage and read changed sources directly; read pending/partial/unavailable/legacy warnings as structural state, never as `extraction is disabled`; see [project knowledge](../guides/project-knowledge.md). |
| Role learning | Reflection aggregates outcome signals, not full answer semantics; lexical search has bounded scale and notes remain agent-reported evidence. | Search/read original notes, correct by expected revision and revalidate old sources. |
| Knowledge activation | Component installation does not enable profile tools or resolve a session automatically when native workspace metadata is absent. | Check `aether knowledge doctor`, plugin enablement and exact session binding; never select the last-used graph. |
| Live reliability/release evidence | Provider-backed model execution, persistent-session wake, protected CI, immutable runtime, and public release qualification remain outside this local build. | Use deterministic tests as local evidence only; do not invoke providers or publish. |

## Provider-free diagnostics

```bash
aether --version
aether --help
aether observe --help
aether doctor --json
aether --project PATH --json
aether reconcile --to active --json
aether knowledge doctor --json
```

A missing active release may make `doctor` return an integrity error. That is an honest diagnostic in a clean environment. `aether --project PATH --json` prints the launch plan and changes nothing, and `aether reconcile --to active` without `--yes` is a non-mutating preview of the projection mismatches it would repair. `observe` needs a resolvable initialized project/observation state; no trace is reported as an explicit empty state, while ambiguous inputs are errors rather than guesses.

`aether update --local --aether-checkout PATH --aether-commit SHA --fork-checkout PATH
--fork-commit SHA` without `--yes` is a safe, non-mutating preview of a local candidate; only
an explicit `--yes` may stage and activate one, and that activation interrupts Aether-owned
instances. A mismatch between the authoritative active-release record, `runtime/current`, the
launcher, or the Desktop entry, or an invalid Hermes-owned service selector, is reported as a
fail-closed doctor diagnostic rather than repaired silently; `aether rollback` returns to the
prior coherent release without rolling user state backward.

## Policy denials

A denial mentioning credential material/acquisition, protected external effect, or destructive operation is a real edge boundary. Stop; do not work around it with another tool or alternate command. An unexpected denial for ordinary local reversible work is a policy regression: follow the rollback-first recovery process in [Policy and recovery](../guides/policy-and-recovery.md) and record the evidence.

## Preservation rules

Do not put credentials, secrets, private profile/configuration content, sessions, board databases, logs, machine paths, or provider/model bindings into documentation, contract envelopes, issue-like durable fields, or public artifacts. The generic authoritative references for Hermes configuration and troubleshooting are at [Hermes Agent documentation](https://hermes-agent.nousresearch.com/docs/).

See [Capability coverage](capabilities.md) for each public surface's current status and evidence paths.
