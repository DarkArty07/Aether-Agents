# Limitations and troubleshooting

This page records the limits of the `1.0.0` release plainly. Features are frozen at this release, so these limits and the [known issues](#known-issues) below are expected to remain. It does not turn a candidate interface, package source file, or historical qualification artifact into a readiness claim.

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
| Installation channel | Installation uses the GitHub Release bundle with `aether setup` and a Git checkout of the pinned Hermes fork. There is no PyPI package, hosted installer, guided wizard or automatic update channel. Setup needs a running systemd user session (on WSL2, `systemd=true` in `/etc/wsl.conf`) and Node.js with npm. | Follow [Installation](../installation.md); move between releases only with `aether update` and `aether rollback`. |
| Managed Hermes source | The executable source is the maintained fork under release-lock source mode `maintained_fork`, emitted as `schema_version` 5 with the closed `hermes.extras` allowlist and still readable as schema 4; the retired `transitional_fork` mode is refused and `.patch` files are never replayed. | Read the release lock for the exact repository, commit, source-tree digest and artifacts; never repair a runtime by applying a patch file. |
| Release scope | `1.0.0` (tag `v1.0.0`) is RC19's product source with stable identity, documentation and assets, on maintained-fork commit `66e87f3487d75cda3681146818006b7c796a71a9`; see the [release record](../../specs/v1-stable-release/spec.md). It is not a PyPI publication, a WSL2 platform qualification or a provider-backed agent-behavior qualification, and the PD-74 reliability gate remains outstanding. | Identify the installed runtime with `aether doctor --json`; source, `VERSION` and tags never prove activation or agent behavior. |
| State export | `uninstall --export` returns `EXPORT_NOT_IMPLEMENTED`. | Preserve state; do not claim an export occurred. |
| Portable profiles | Resources are versioned candidate bytes, not proof of live profile activation. | Avoid copying private profile state into project artifacts. |
| Morfeo toolsets | The packaged Morfeo profile does not select toolsets, and launch requires `file` and `kanban` (`missing required Morfeo toolsets`). | Add them once to the Morfeo profile; see [Installation, step 5](../installation.md#5-configure-a-model-for-each-role). |
| Optional Graphify | Structural graphs are committed-revision snapshots; configured semantic maintenance is opt-in (`semantic.enabled` plus a bound auxiliary task), bounded to one 300-second update, and dirty files are not indexed. Its semantics are an additive `origin=llm` overlay, and a snapshot without the current integrity identity is reported as untrusted structural state rather than a trusted semantic result. | Check revision/coverage and read changed sources directly; read pending/partial/unavailable/legacy warnings as structural state, never as `extraction is disabled`; see [project knowledge](../guides/project-knowledge.md). |
| Role learning | Reflection aggregates outcome signals, not full answer semantics; lexical search has bounded scale and notes remain agent-reported evidence. | Search/read original notes, correct by expected revision and revalidate old sources. |
| Knowledge activation | Component installation does not enable profile tools or resolve a session automatically when native workspace metadata is absent. | Check `aether knowledge doctor`, plugin enablement and exact session binding; never select the last-used graph. |
| Live reliability evidence | Provider-backed model execution, persistent-session wake and live agent reliability are not qualified; deterministic tests and the release bundle's clean-install probes are the evidence shipped with `1.0.0`. | Treat agent conduct as model-dependent; verify results from commands, diffs and tests. |

## Known issues

These defects were open when features were frozen at `1.0.0`. They are documented here
instead of being fixed; check each issue for its current state and any workaround.

| Issue | Effect | Workaround |
| --- | --- | --- |
| [#558](https://github.com/DarkArty07/Aether-Agents/issues/558) | `morfeo_bootstrap` returns about 70,000 characters, above Claude Code's default MCP output limit, so the host spills it to a file. | Start Claude Code with a higher `MAX_MCP_OUTPUT_TOKENS`, for example `60000`. |
| [#557](https://github.com/DarkArty07/Aether-Agents/issues/557) | Morfeo over MCP ignores the profile's configured memory limits. | Keep Morfeo's memory files concise. |
| [#559](https://github.com/DarkArty07/Aether-Agents/issues/559) | The Morfeo MCP qualification lists the knowledge tools but never invokes them. | None needed for use; it is a test-coverage gap. |
| [#553](https://github.com/DarkArty07/Aether-Agents/issues/553) | Contract alerts and terminal results do not wake Morfeo in the originating TUI session. | Ask Morfeo for status, or run `aether observe`. |
| [#560](https://github.com/DarkArty07/Aether-Agents/issues/560) | `aether doctor` does not show why active-release revalidation failed. | Read `diagnostic_codes` in `aether doctor --json`. Never edit an installed release; use `aether reconcile --to active` or `aether rollback`. |
| [#539](https://github.com/DarkArty07/Aether-Agents/issues/539) | The edge policy denies deleting a merged remote work branch. | Delete merged branches yourself, for example in the GitHub UI. |
| [#561](https://github.com/DarkArty07/Aether-Agents/issues/561) | A code comment calls the gateway unit Aether-owned, although Hermes owns it. | None; the behavior matches the documentation. |

The enhancements [#316](https://github.com/DarkArty07/Aether-Agents/issues/316) (Hermes Web
Dashboard surface) and [#491](https://github.com/DarkArty07/Aether-Agents/issues/491)
(non-blocking Graphify updates) remain open without a delivery commitment. A local release
bundle built from a fork checkout that has Git tags records the nearest ancestor tag in its
lock, which `aether setup` then refuses. The published bundles are built from a tagless
fetch and are not affected.

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
