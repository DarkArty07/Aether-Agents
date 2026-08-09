# M5.4 Model-Backed Swarm Acceptance

## Verdict

`BLOCKED_MODEL_WORKER_TIMEOUT / UC_C05_PASS / UC_C03_INSUFFICIENT`

M5.4 is **not accepted**. The admitted Orca/Codex slice passed pre-effect
authority denials, created two supervised worker receipts before artifact polling,
and cleaned all task-owned resources, but neither worker produced its required
artifact within the 600-second hard stop. Real overlap, implementation quality,
peer handoff and coordinator integration therefore remain unproved.

This verdict does not alter the accepted deterministic M5 boundary in
`M5_PARALLEL_ACCEPTANCE.md`. Deterministic fixtures are not reported as model
behavior.

Canonical evidence:

- `M5_MODEL_BACKED_EVIDENCE.json` — final aggregate and cleanup;
- `M5_MODEL_BACKED_ABORTED_EVIDENCE.json` — preserved pre-model receipt-drift
  failure from the first framework-path attempt.

## Admitted slice

The product owner authorized all remaining local effects for this qualification.
The bounded candidate used:

- Orca `1.4.167` through its desktop renderer and public structured CLI;
- Codex CLI `0.146.0` with system-default OAuth;
- exact configured model `gpt-5.6-terra`;
- two independent workers, one corrected-run launch per worker and no model retry;
- 600 seconds maximum per worker;
- existing subscription quota only, no authorized PAYG charge;
- no web use, deployment, remote mutation, MCP registration or activation.

A new isolated Orca profile could not admit the existing system OAuth account
without reauthentication. The owner authorized the fallback: isolated fixture
worktrees and Aether state over the persistent Orca profile, with a protected
post-reset metadata snapshot and exact hash-verified rollback. This is recorded
as an isolation deviation and is not evidence of pure isolated-profile support.

## Preflight

Preflight established before the corrected run:

- system-default Codex OAuth was available;
- Orca's managed Codex baseline resolved exactly to `gpt-5.6-terra`;
- weekly usage was reported as `0%` at integer-percent resolution;
- zero terminals existed;
- only Orca's regenerated `run_legacy_local` sentinel existed;
- the candidate fixture repo had not yet been registered;
- the stdio MCP server remained default-off with zero callable tools.

## UC-C05 — pre-effect denial

UC-C05 passes for the bounded cases. Each invalid request was rejected before a
provider mutation:

| Case | Stable code | Provider effects |
|---|---|---:|
| Overlapping write scopes | `WRITE_SCOPE_CONFLICT` | 0 |
| Forbidden participant | `PARTICIPANT_FORBIDDEN` | 0 |
| Dependency cycle | `DEPENDENCY_CYCLE` | 0 |
| Protected effect without authority | `EFFECT_NOT_AUTHORIZED` | 0 |
| Free-text authority expansion | `EFFECT_NOT_AUTHORIZED` | 0 |

The final focused catalog, coordination and public-provider contracts passed
`18/18` after the receipt correction and no-fallback retry guard.

## Preserved framework-path failure

The first live path returned a valid Orca worker-start Dispatch identity but the
initial provider adapter incorrectly expected terminal and worktree identities in
the same receipt. Aether stopped before admitting the logical Dispatch, reset the
runtime and preserved the failure.

The correction composes two public structured commands:

1. `orchestration worker-start` for the provider Dispatch identity;
2. `orchestration worker-show` for terminal, worker and worktree placement.

No private database, undocumented API, UI parsing, compatibility shim or hidden
fallback was introduced. Subscription usage still reported `0%` after the abort.

## UC-C03 — model-backed parallelism

The corrected qualifier returned two worker-start receipts before entering its
artifact wait loop. This proves ordering of provider admission, but it does not
prove useful model execution or concurrency.

At the hard stop:

- backend artifact: absent;
- frontend artifact: absent;
- accepted model outputs: 0;
- observable real overlap: unknown;
- quality checks: not executable;
- peer handoff: not executed;
- coordinator integration: not executed;
- automatic retries: 0.

The task contract required cleanup and stop on timeout. No retry was performed.
M5.4 therefore fails its UC-C03 acceptance condition.

## Usage and privacy

Codex weekly usage reported `0%` before and after the bounded attempts. That
coarse integer-percent result is **not** treated as proof of zero tokens. Exact
tokens and cost remain unknown. PAYG spending was neither authorized nor
configured.

Orca's managed Codex runtime metadata changed during the launches. Protected
SQLite and transcript content was not opened, exported or retained. No raw model
conversation appears in release evidence.

## Cleanup and rollback

Final deterministic checks established:

- zero Orca terminals;
- zero candidate Runs; the pre-existing legacy sentinel is preserved;
- zero owned processes;
- zero mounts;
- zero X displays;
- zero temporary qualification roots;
- Orca runtime not running;
- persistent Orca metadata restored exactly to SHA-256
  `0762617bd57d80078af2be61499e339ee556c780c83176038d8a2a4a4446455f`;
- the temporary fixture-repository registration removed by rollback.

No push, PR, merge, tag, Release, deployment, persistent service, credential
creation or MCP activation occurred.

## Stop condition

The authorized run is closed at `BLOCKED_MODEL_WORKER_TIMEOUT`. Deterministic M5
remains accepted, while model-backed multi-agent execution remains unavailable.
A future attempt requires a new bounded gate with provider-start observability
sufficient to explain worker readiness before spending another model attempt.
