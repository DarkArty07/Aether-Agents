# M5.4 Worker Liveness Investigation and Correction

## Status

`ACCEPTED — LIVE REQUALIFICATION PASSED`

This document records the investigation opened after the bounded M5.4 run at
`1aef9ee` returned two Orca `worker-start` receipts but no accepted model artifact
within the 600-second hard stop, and the corrections that culminated in an exact
bounded live pass. `M5_4_MODEL_ACCEPTANCE.md` carries the final verdict while all
intermediate failures remain preserved below.

## Preserved failure

The prior run established all of the following:

- two Codex workers were admitted through public Orca commands before artifact
  polling;
- both worker processes remained live until the hard stop;
- neither child worktree contained its required `model-result.json` marker or any
  implementation change;
- account telemetry remained at the same coarse `0%` value before and after;
- cleanup removed every task-owned terminal, worker, worktree and process;
- no retry, fallback worker, PAYG spend, publication or activation occurred.

Retained non-secret Codex metadata contained no new thread or log record in the
run interval. Because the terminal transcript was not read before cleanup, that
metadata cannot distinguish a lost prompt submit from a provider request stalled
before the first observable model activity. The historical verdict therefore
remains truthful: useful model execution and overlap were not proved.

## Exact Orca 1.4.167 behavior

Static inspection of the exact extracted build established this sequence:

1. `orchestration worker-start` waits for `tui-idle`;
2. it calls `sendTerminalAgentPrompt`;
3. that method writes bracketed-paste bytes, waits 500 ms and writes carriage
   return;
4. a successful PTY write returns `accepted=true`;
5. `worker-start` then returns state `ready` without awaiting a Codex
   `UserPromptSubmit`, provider session, transcript or `working` transition.

The same build's public `worker-read --source auto` has the missing distinction:
it returns structured transcript output only after an exact provider session is
reported; otherwise it falls back to redacted terminal output with a reason such
as `session_not_reported`. A `worker-start` receipt is therefore process/input
admission evidence, not model-execution liveness evidence.

## No-model reproduction

Four isolated, reversible probes used Orca 1.4.167 and Codex 0.146.0 without
sending an inference prompt:

- `tui-idle` stabilized in 2.322–4.286 seconds;
- the TUI displayed OpenAI Codex, the configured `gpt-5.6-terra` model and the
  expected directory;
- `/status` was consumed through normal terminal input;
- `/status` was also consumed through the exact bracketed-paste framing used by
  `sendTerminalAgentPrompt`;
- `/model` was consumed and continued to display `gpt-5.6-terra`;
- no authentication, trust, hook-review, command-not-found or unknown-model modal
  appeared;
- a synthetic empty `UserPromptSubmit` hook invocation exited 0 in 0.006 seconds;
- every probe closed with zero owned process survivors and removed its temporary
  root.

These probes ruled out a general PATH, OAuth, trust, startup-readiness,
bracketed-paste, Enter, hook or configured-model display failure. An early PATH
hypothesis was explicitly rejected because the model qualifier already prepends
`~/.local/bin` to the isolated runtime PATH.

## Correction contract

The correction keeps Orca as the only mutable runtime authority and composes only
its public structured CLI:

1. both workers are still dispatched before any liveness or artifact polling;
2. Aether calls `worker-read --source auto --limit 200` for each exact provider
   Dispatch;
3. raw terminal/transcript content remains in memory only; evidence stores only
   source, bounded classification, byte count and SHA-256 digest;
4. liveness is accepted only from either:
   - the required task-scoped `model-result.json` marker in `working` or `passed`
     state with a valid start timestamp; or
   - a non-empty exact public provider transcript;
5. a classified auth, model, quota, hook, launch or network block fails
   immediately;
6. if no provider session exists and the public terminal view still has an idle
   Codex prompt, Aether may send exactly one empty `Enter` to the exact terminal;
   it never resends prompt text and never creates a second model attempt;
7. absence of liveness after 90 seconds fails as
   `ERR_MODEL_PROMPT_NOT_ACKNOWLEDGED` with a sanitized summary;
8. the liveness phase and completion phase share the original 600-second hard
   stop rather than adding 90 seconds to it.

The one empty `Enter` is input-delivery recovery, not a model retry. If the public
state cannot safely justify it, the qualifier performs no recovery and fails
closed.

## Difficulty and resolution log

### D1 — existing-runtime identity drift

The first corrected requalification wrapper started Orca successfully but the
qualifier could not observe it because each process had a different isolated XDG
runtime identity. The run stopped before worker creation or model use. The
persistent Orca profile was restored byte-for-byte with matching SHA-256 and no
process survivor.

Resolution: retain the preferred isolated qualifier path instead of broadening
the persistent runtime boundary.

### D2 — regenerated legacy sentinel in isolated XDG

The isolated no-model preflight initially rejected Orca's automatically
regenerated `run_legacy_local`. The prior condition admitted that exact sentinel
only for a persistent profile even though the exact build creates it in a new
isolated profile as well.

Resolution: admit either zero Runs or exactly one `run_legacy_local` with
`legacy=1` in both modes. Every other Run identity or shape still fails closed.
The boundary has deterministic positive and negative coverage. The corrected
isolated preflight passes without a model call.

### D3 — Codex update prompt blocks Orca readiness

The first real isolated attempt after the observability correction did not reach
prompt delivery. Orca returned a structured failed Dispatch at
`stage=agent_readiness` with `lastError=Agent startup blocked:
codex-update-prompt`. This explains the previously opaque worker startup: Codex
0.146.0 presented an interactive update surface that Orca correctly refused to
treat as `tui-idle`.

Resolution: the product owner explicitly authorized updating the local Codex CLI
on 2026-08-09. `codex update` selected its supported npm installation path and
updated `@openai/codex` from `0.146.0` to `0.147.0` successfully. The executable
remains `/home/darkarty/.local/bin/codex`; no login, logout, credential copy or
OAuth mutation was performed. The blocked attempt is preserved separately in
`M5_MODEL_LIVENESS_UPDATE_BLOCK_EVIDENCE.json`. The next gates are the isolated
no-model preflight followed by one bounded model qualification. If readiness
remains blocked, the new exact reason is preserved and execution stops without
another retry.

### D4 — final marker replaced its witnessed start timestamp

The first bounded qualification with Codex 0.147.0 passed readiness for both
workers. Backend and frontend each created a valid `working` marker without
submit recovery, later produced a `passed` marker, and reached frozen-verifier
validation. The run then failed closed as `frontend timing report is invalid`.
The qualifier had already witnessed a valid integer `started_at_ns` in the
frontend's initial marker, but retained only the marker status; final validation
incorrectly depended on the worker preserving that field when rewriting the
`passed` JSON. Evidence is preserved in
`M5_MODEL_LIVENESS_TIMING_BLOCK_EVIDENCE.json`.

Resolution: liveness evidence now retains the witnessed initial timestamp and
makes it the authoritative interval start. A final marker may omit that field,
but if it includes one it must exactly match the witnessed value. A
transcript-only acknowledgement still requires the final marker to provide a
valid start. This does not fabricate timing or weaken overlap: it preserves the
earlier value read directly from the worker artifact and rejects contradictory
values. Deterministic tests cover missing, matching-source and contradictory
final timing.

### D5 — second corrected candidate stopped at frontend launch

After D4 was corrected and Ruff, compileall, 21 focused tests and 197 repository
tests passed, the next bounded candidate failed during frontend liveness with
`ERR_MODEL_TERMINAL_BLOCKED:frontend:launch`. It created no new Codex rollout,
which places the failure before provider-session establishment. Cleanup again
reported zero owned process, display and mount survivors. The sanitized evidence
is preserved in `M5_MODEL_LIVENESS_LAUNCH_BLOCK_EVIDENCE.json`.

Resolution: the same two Orca worker-start paths were exercised with `/status`
as the complete agent prompt and a 15-second diagnostic timeout. Both reached
public `source=transcript`, neither reported a blocked reason or required submit
recovery, and the expected terminal condition was only
`ERR_MODEL_PROMPT_NOT_ACKNOWLEDGED` because the no-model probe deliberately
created no `model-result.json`. Cleanup had zero owned process, display and mount
survivors. The result is preserved in
`M5_TWO_WORKER_READINESS_PROBE_EVIDENCE.json`. The launch failure is therefore
non-reproduced startup instability, not a deterministic Codex 0.147.0
incompatibility. One final model-backed candidate is permitted under the
unchanged one-attempt-per-worker contract; another startup failure stops the
sequence.

### D6 — final transcript digest used a stale Orca flag

The candidate after the successful no-model readiness probe advanced past both
`working` markers, model completion, frozen verification, overlap proof, worker
completion and integration. It then failed before semantic close while collecting
the final transcript digests: the qualifier used `worker-read --chars 20000`,
but Orca 1.4.167 exposes `--limit` and returned its exact valid-flag catalog.
The incomplete candidate and zero-survivor cleanup are preserved in
`M5_MODEL_LIVENESS_READ_FLAG_BLOCK_EVIDENCE.json`; it is not accepted because the
full evidence object and semantic close did not complete.

Resolution: replace the inline call with one testable `worker_read_command`
builder that emits `--source auto --limit 20000 --json`. Its RED/GREEN contract
asserts the complete argv and explicitly rejects `--chars`. The provider's
liveness observation already used the correct public `--limit 200` path; no
provider behavior was broadened.

### D7 — corrected model-backed candidate passed

The final isolated candidate used Orca 1.4.167, Codex CLI 0.147.0, system-default
OAuth and exact model `gpt-5.6-terra`. It passed with:

- two Dispatch receipts issued before polling;
- independent backend and frontend `working` markers with zero submit recovery;
- two model reports in `passed` state and both frozen verifiers at exit 0;
- a positive model-execution interval overlap;
- two technically completed worker messages, coordinator integration of both
  component digests and semantic Run close;
- five UC-C05 pre-effect denials with zero provider effects;
- zero retries and USD 0 PAYG spend;
- transcript digests only, with no raw transcript retained; and
- zero owned process, display, mount, worktree-metadata or isolated-root
  survivors.

Canonical result: `M5_MODEL_LIVENESS_CORRECTED_EVIDENCE.json` with status
`PASS_MODEL_BACKED_M5_4`.

## Deterministic evidence

Test-first coverage records the correction:

- provider observation reports transcript activity without retaining prompt or
  transcript text;
- submit recovery emits exactly
  `terminal send --terminal <exact-handle> --enter --json`, with no `--text`;
- an initial `working` marker acknowledges liveness without terminal recovery;
- one idle recovery followed by transcript activity is accepted;
- a public blocked reason fails immediately without an Enter;
- a no-activity timeout is sanitized and does not resend the prompt;
- the witnessed initial marker supplies the authoritative interval start while
  contradictory final timing is rejected; and
- transcript digest reads use Orca's exact public `--limit` flag.

The corrected live candidate passed after Ruff, compileall, 22 focused tests and
198 repository tests. This accepts only the exact bounded
desktop-renderer-plus-public-CLI path; it does not establish pure headless
admission, MCP registration, persistent service activation or general deployment.
