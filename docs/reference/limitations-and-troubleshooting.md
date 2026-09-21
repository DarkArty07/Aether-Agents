# Limitations and troubleshooting

This page records current limits plainly. It does not turn a candidate interface, package source file, or historical qualification artifact into a release/readiness claim.

## Current limits

| Area | Current limit | Safe response |
| --- | --- | --- |
| Greenfield initialization | `aether init` requires an existing Git repository root; it does not run `git init`. | Create/use a Git root and an exact-path native Hermes Project first. |
| Native Project binding | `init` refuses missing, ambiguous, or mismatched exact `primary_path` matches. | Correct the native Hermes Project or pass `--hermes-project` only for an exact match. |
| Bare project launch | The source-tree launcher has local prerequisites; installed project-aware launch is not fully qualified. | Use `--help`, `--version`, and `doctor` for discovery; do not infer a release-ready TUI path. |
| Project-aware doctor | `doctor --project` is accepted but the full project mapping diagnosis is unfinished. | Treat result as lifecycle coherence evidence only. |
| Service lifecycle | `start`, `stop`, `restart`, and `status` return explicit unsupported results. | Do not expect this build to activate or control a service. |
| Reconciliation | `reconcile` returns explicit unsupported. | Do not use it to repair an external package-manager mismatch. |
| Guided/declarative setup | Only a local wheel/check-out/release-lock candidate interface exists. | Do not treat it as a clean public installation wizard. |
| Managed Hermes source | The executable source is the maintained fork under release-lock `schema_version` 4 source mode `maintained_fork`; the retired `transitional_fork` mode is refused and `.patch` files are never replayed. | Read the release lock for the exact repository, commit, source-tree digest and artifacts; never repair a runtime by applying a patch file. |
| Release-candidate scope | The authorized `1.0.0rc1` / `v1.0.0-rc.1` milestone is pre-stable; its annotated GitHub prerelease `v1.0.0-rc.1` is published from this repository at the tagged commit without being accepted for activation. It is not stable `1.0.0`, not a package-index publication and not WSL2-qualified. | Treat `release_channel = prerelease` as a bounded milestone only; never read the publication as acceptance and do not activate it; issue #261 remains open with the stable, PyPI/OIDC and WSL2 gates outstanding. |
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
aether knowledge doctor --json
```

A missing active release may make `doctor` return an integrity error. That is an honest diagnostic in a clean environment. `observe` needs a resolvable initialized project/observation state; no trace is reported as an explicit empty state, while ambiguous inputs are errors rather than guesses.

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
