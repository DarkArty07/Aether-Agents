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
| State export | `uninstall --export` returns `EXPORT_NOT_IMPLEMENTED`. | Preserve state; do not claim an export occurred. |
| Portable profiles | Resources are versioned candidate bytes, not proof of live profile activation. | Avoid copying private profile state into project artifacts. |
| Live reliability/release evidence | Provider-backed model execution, persistent-session wake, protected CI, immutable runtime, and public release qualification remain outside this local build. | Use deterministic tests as local evidence only; do not invoke providers or publish. |

## Provider-free diagnostics

```bash
aether --version
aether --help
aether observe --help
aether doctor --json
```

A missing active release may make `doctor` return an integrity error. That is an honest diagnostic in a clean environment. `observe` needs a resolvable initialized project/observation state; no trace is reported as an explicit empty state, while ambiguous inputs are errors rather than guesses.

## Policy denials

A denial mentioning credential material/acquisition, protected external effect, or destructive operation is a real edge boundary. Stop; do not work around it with another tool or alternate command. An unexpected denial for ordinary local reversible work is a policy regression: follow the rollback-first recovery process in [Policy and recovery](../guides/policy-and-recovery.md) and record the evidence.

## Preservation rules

Do not put credentials, secrets, private profile/configuration content, sessions, board databases, logs, machine paths, or provider/model bindings into documentation, contract envelopes, issue-like durable fields, or public artifacts. The generic authoritative references for Hermes configuration and troubleshooting are at [Hermes Agent documentation](https://hermes-agent.nousresearch.com/docs/).

See [Capability coverage](capabilities.md) for each public surface's current status and evidence paths.
