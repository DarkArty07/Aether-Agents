# M5.4 Model-Backed Swarm Acceptance

## Verdict

`ACCEPTED_MODEL_BACKED_M5_4 / UC_C05_PASS / UC_C03_PASS`

M5.4 is accepted for one bounded Orca/Codex slice. The corrected candidate passed
pre-effect authority denials, issued two supervised Dispatch receipts before
polling, established task-scoped model liveness, produced two independently
verified artifacts with real execution overlap, completed provider-correlated
worker messages, integrated both artifacts and closed with zero survivors.

This verdict does not alter the accepted deterministic M5 boundary in
`M5_PARALLEL_ACCEPTANCE.md`. Deterministic fixtures are not reported as model
behavior, and the live pass does not imply pure headless support, MCP registration,
persistent service activation or general deployment.

Canonical evidence:

- `M5_MODEL_BACKED_EVIDENCE.json` — final aggregate and cleanup;
- `M5_MODEL_BACKED_ABORTED_EVIDENCE.json` — preserved pre-model receipt-drift
  failure from the first framework-path attempt;
- `M5_MODEL_LIVENESS_CORRECTED_EVIDENCE.json` — accepted isolated live aggregate;
- `M5_MODEL_LIVENESS_UPDATE_BLOCK_EVIDENCE.json`,
  `M5_MODEL_LIVENESS_TIMING_BLOCK_EVIDENCE.json`,
  `M5_MODEL_LIVENESS_LAUNCH_BLOCK_EVIDENCE.json` and
  `M5_MODEL_LIVENESS_READ_FLAG_BLOCK_EVIDENCE.json` — preserved correction-path
  failures;
- `M5_TWO_WORKER_READINESS_PROBE_EVIDENCE.json` — bounded no-model two-worker
  readiness probe; and
- `M5_4_WORKER_LIVENESS_CORRECTION.md` — retained-metadata investigation,
  difficulty log, no-model probes and implemented corrections.

## Admitted slice

The product owner authorized all remaining local effects for this qualification.
The bounded candidate used:

- Orca `1.4.167` through its desktop renderer and public structured CLI;
- Codex CLI `0.147.0` with system-default OAuth;
- exact configured model `gpt-5.6-terra`;
- two independent workers, one launch per worker in the accepted candidate and no
  model retry;
- 600 seconds maximum per worker;
- existing subscription quota only, no authorized PAYG charge;
- no web use, deployment, remote mutation, MCP registration or activation.

The accepted run used isolated XDG state and a temporary HOME that linked only the
existing Codex runtime account directory. Orca orchestration state, fixture
worktrees and Aether evidence state remained isolated; no reauthentication,
credential copy or persistent Orca-profile rollback was required. This still does
not establish a pure headless Orca admission surface because the exact binding
uses the desktop renderer.

## Preflight

Preflight established before the accepted run:

- system-default Codex OAuth was available;
- Orca's managed Codex baseline resolved exactly to `gpt-5.6-terra`;
- Codex CLI resolved exactly to `0.147.0` in the worker environment;
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

The final focused coordination, public-provider and qualifier contracts passed
`22/22`; the repository suite passed `198/198`.

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

The accepted qualifier returned two Dispatch receipts before liveness or artifact
polling. Backend and frontend then independently wrote valid `working` markers;
neither required the one-shot empty-Enter recovery.

The accepted evidence establishes:

- backend and frontend model reports identify exact model `gpt-5.6-terra` and
  status `passed`;
- backend frozen verifier `python3 acceptance/verify_backend.py` exited 0;
- frontend frozen verifier `node acceptance/verify_frontend.mjs` exited 0;
- the witnessed model-execution intervals have a positive overlap;
- both Dispatches completed as `TECHNICALLY_COMPLETED` with distinct artifact and
  evidence digests;
- coordinator integration contains exactly the two accepted component digests;
- final public worker-read responses are retained only as byte counts and SHA-256
  digests;
- semantic close returned `CLOSED` with zero survivors; and
- automatic model retries: 0.

UC-C03 therefore passes for this exact bounded slice.

## Post-timeout investigation

The follow-up investigation established that Orca `worker-start` state `ready`
acknowledges PTY prompt bytes, not a Codex provider session or first model
activity. Exact-build no-model probes ruled out a general launch, OAuth, trust,
bracketed-paste, Enter, hook or configured-model display failure. Retained
metadata cannot distinguish a lost submit from a provider stall because the
original run did not capture `worker-read` before cleanup.

The repository correction now requires a task marker or non-empty exact public
transcript within 90 seconds, records only sanitized classifications and digests,
permits at most one empty Enter without resending prompt text, and shares the
original 600-second hard stop. The initial timeout remains preserved historical
evidence; the later corrected candidate passed every bounded gate. Detailed
difficulties and resolutions, including the Codex update, timing witness and
public `worker-read --limit` correction, are recorded in
`M5_4_WORKER_LIVENESS_CORRECTION.md`.

## Usage and privacy

The accepted run's preflight did not expose a weekly percentage; its post-run
account response reported `0%` at integer-percent resolution. That coarse value
is **not** treated as proof of zero tokens. Exact tokens and subscription cost
remain unknown. Recorded PAYG spending is USD 0; PAYG was not authorized.

Orca's managed Codex runtime metadata changed during the launches. Raw transcript
content was not retained; release evidence stores only public-response byte counts
and SHA-256 digests. No secret, credential, production data or web content was
sent to either worker.

## Cleanup and rollback

Final live and deterministic checks established:

- zero Orca terminals;
- zero owned processes;
- zero mounts;
- zero X displays;
- zero temporary qualification roots;
- Orca runtime not running;
- semantic close returned `CLOSED` with no retained resources;
- child worktrees and temporary fixture registration were removed; and
- isolated XDG/Aether state was deleted without mutating persistent Orca
  orchestration metadata.

No push, PR, merge, tag, Release, deployment, persistent service, credential
creation or MCP activation occurred.

## Stop condition

The authorized correction sequence is closed at `ACCEPTED_MODEL_BACKED_M5_4` for
the exact Orca 1.4.167 desktop-renderer plus public-CLI binding with Codex CLI
0.147.0 and model `gpt-5.6-terra`. Deterministic M5 remains accepted. This does not
establish pure headless admission, expose or register an MCP tool, activate a
persistent runtime, authorize deployment, or generalize the result beyond the
bounded synthetic two-worker slice.
