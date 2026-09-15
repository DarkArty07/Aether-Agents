# Policy and recovery

Aether's normal local safety model is reversibility-first: scope, worktrees, Git,
tests, review, and rollback protect ordinary local work. The shared pre-tool
policy is deliberately small and does not interpret product ownership, task
size, route selection, board state, or arbitrary command semantics.

## What the policy protects

The versioned policy for all three role resources blocks only high-confidence edge
effects and malformed hook payloads:

- credential-shaped material in durable fields or obvious tool input;
- credential acquisition, key generation, or access widening;
- protected remote/external mutation, deployment, package/container publication,
  infrastructure mutation, or arbitrary mutating API calls; and
- clearly destructive irreversible local operations such as device/root/home
  destruction.

It permits ordinary reversible local editing, tests, branches, local commits,
normal local Git operations, and unfamiliar local tools that do not match a
protected family. Routine closeout within the provisioned repository and with
existing credentials is not a protected bypass. It does not authorize:

- credential acquisition/widening;
- settings mutation;
- force/history rewrite;
- package publication;
- deployment; or
- destructive/bypass variants.

A genuine protected-edge denial is authoritative. Never route around it through
another tool or a different command shape.

## Recovery boundary

If the policy unexpectedly denies ordinary local reversible work, treat it as an
Aether regression. Recovery is rollback-first and bounded:

1. retry or resume only when safely transient;
2. otherwise restore the last known-good behavior;
3. make at most two focused repairs only when rollback cannot restore it; and
4. stop once the canary passes, recording hardening as a separate objective.

Recovery does not authorize a new feature, an enlarged protected-effect list, a
new contract, provider use, credential acquisition, deployment, publication, or a
replacement workflow. If the problem is an out-of-scope product defect rather
than the mechanism blocking the work, record it instead of silently fixing it.

## Candidate lifecycle commands

`setup`, `update`, `rollback`, and `uninstall` have local planning/confirmation
logic. They are candidate lifecycle surfaces, not proof of a public release. In
particular, `uninstall --export` returns an explicit unavailable error, and a
destructive purge requires confirmation. See [CLI reference](../reference/cli.md)
and [limitations](../reference/limitations-and-troubleshooting.md).

### `aether update` is the promotion boundary

`aether update` is the only supported promotion and activation boundary for the managed
runtime. Nothing else stages, switches or activates a release, and no update runs on
startup or a timer.

The local-candidate route takes explicit identities — `aether update --local
--aether-checkout PATH --aether-commit SHA --fork-checkout PATH --fork-commit SHA` — and
is mutually exclusive with `[VERSION]`, `--prerelease`, `--wheel`, `--hermes-checkout`
and `--release-lock`. Without `--yes` (or with `--dry-run`) it is a non-mutating preview
that reports the exact revisions, target version and release ID, active HLP coverage,
artifacts and hashes, expected service interruption, preserved state and any blockers. A
dirty tree, an ambiguous or missing checkout, a wrong repository or branch, an unknown or
mismatched commit, a bad hash or an incompatible Python is refused without staging or
activation, and identity is never taken from the current directory, checkout recency or a
mutable branch tip.

Activation is explicit and may interrupt Aether-owned TUI, gateway and worker processes
immediately; there is no drain or wait-for-idle semantics. Unrelated Hermes installations
and services keep running. A partial transition is detected and recoverable instead of
being reported as success, and `aether rollback` restores product code, runtime and service
without rolling user state backward.

Release-lock `schema_version` 4 declares the maintained-fork source identity
(`hermes.source_mode = maintained_fork`, `hermes.repository =
https://github.com/DarkArty07/aether-hermes`); the retired `transitional_fork` mode — a
fixed public baseline plus replayed `.patch` files — is refused for new preparation, and
`.patch` records are never applied to an active release.
