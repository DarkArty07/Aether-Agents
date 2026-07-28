# Phase 0 Evidence — Aether v0.19.0 Autonomous Coordination

**Date:** 2026-07-18
**Phase:** R1 / feasibility proof
**Exit:** **GO WITH NAMED LIMITS**
**Runtime state:** tests-only; no coordination runtime exists or is enabled

## 1. Decision

Phase 0 establishes that Aether can begin R2, the Cotal-inspired protocol and immutable-contract layer, without replacing Olympus/ACP lifecycle ownership and without touching the live Telegram gateway.

This is not an unconditional runtime GO. It authorizes only default-off production TDD under the phase gates below.

| Seam | Verdict | Meaning |
|---|---|---|
| Olympus lifecycle | **GO WITH NAMED LIMITS** | Existing `ACPManager` remains the only process/session owner. The future adapter may call its public operations but may not reproduce lifecycle state or process management. |
| SQLite store | **GO WITH NAMED LIMITS** | Stdlib SQLite is feasible for isolated TDD. The current helper is disposable proof code, not the R3 ledger. R3 remains blocked on the security invariants in §8. |
| Identity/capabilities | **GO WITH NAMED LIMITS** | A tests-only fail-closed authorization contract binds all required dimensions. Real PoP identity, key custody, revocation, and runtime binding remain R4 work. |
| Effect boundary | **GO WITH NAMED LIMITS** | Installed `pre_tool_call` can block before dispatch but is fail-open on exceptions and is therefore shadow-only. E2–E4 enforcement requires the authoritative fail-closed boundary in §6. |
| Recovery | **GO WITH NAMED LIMITS** | Deterministic rebuild, backup, contention, dedupe, and retry mechanics are feasible in isolation. Signed checkpoints, persisted rebuild equivalence, poison handling, and real Olympus reconciliation remain blocked for later phases. |
| Gateway isolation | **GO** | All proofs used test doubles and temporary paths. No gateway, Telegram, service, live database, or production source was changed. |

**R1 result:** **GO WITH NAMED LIMITS**. R2 may start. R3, R4, R5, R6, activation, pilot, merge, tag, and publication retain their own explicit gates.

## 2. Evidence classification

- **VERIFIED:** read directly from current source or exercised by an actual test command.
- **PROVEN IN ISOLATION:** executable behavior in tests-only code or a monkeypatched installed seam.
- **INFERRED:** design consequence consistent with source but not yet exercised through a production adapter.
- **DEFERRED:** intentionally required by a later roadmap gate.
- **UNKNOWN:** insufficient evidence; cannot be claimed.

## 3. Olympus/ACP lifecycle authority

### 3.1 VERIFIED ownership map

| Capability | Current owner and evidence |
|---|---|
| Live process state | `src/olympus_v3/acp_manager.py:59-80` — `AgentState` owns ACP connection, async process context, process, PID, and ACP session map; `SessionInfo` correlates local and remote sessions with `project_root`. |
| Project correlation | `src/olympus_v3/acp_manager.py:172-180` keys agents by `(agent_name, project_root)`. |
| Spawn and ACP session creation | `src/olympus_v3/acp_manager.py:218-293` creates/reuses the agent and calls `connection.new_session()`; `:295-365` calls `spawn_agent_process()`, initializes ACP, and stores process ownership. |
| Message dispatch | `src/olympus_v3/acp_manager.py:415-498` resolves the correlated ACP session and calls `connection.prompt()`; technical stop reason updates in-memory and SQLite status. |
| Poll | `src/olympus_v3/acp_manager.py:504-528` reads technical progress from Olympus SQLite and merges terminal in-memory status. |
| Close/cancel | `src/olympus_v3/acp_manager.py:534-607` calls ACP close/cancel, updates technical status, and releases session mappings. |
| Process teardown | `src/olympus_v3/acp_manager.py:761-853` owns session closure and the process context; terminate/kill are bounded fallbacks. |
| MCP routing | `src/olympus_v3/server.py:293-399` routes open/message/poll/close/cancel to `ACPManager` and steering to Olympus DB; `:402-424` begins delegate through the same manager. |
| Turn/tool observation | `src/olympus_v3/olympus_v3_hooks/hooks.py:129-225` persists turns and post-dispatch tool calls. |
| Steering injection | `src/olympus_v3/olympus_v3_hooks/hooks.py:255-291` consumes DB steering in `pre_llm_call`. |

### 3.2 Adapter invariant

Harmonia and the future Olympus Runtime Adapter may coordinate intent and call existing `ACPManager` operations. They must not:

- call `spawn_agent_process()` directly;
- create or own `AgentState`, `SessionInfo`, `process_context`, PID maps, or ACP connections;
- reinterpret delivery acknowledgement or ACP technical completion as semantic completion;
- terminate, kill, close, or cancel outside `ACPManager`;
- call `shutdown_agent(name)` without `project_root`, because `acp_manager.py:761-781` documents that omission targets every project using that profile.

### 3.3 Named limits

- Request-level correlation is incomplete: `send_message()` does not currently assign/persist an ACP `message_id`.
- Olympus `sessions` has no `project_root` column; isolation depends on per-project paths/environment plus in-memory correlation.
- The adapter does not exist, so exclusivity must be proved again in R5 with production code.
- Orphan-process reconciliation and global server-shutdown integration remain unproved.

## 4. SQLite feasibility proof

### 4.1 PROVEN IN ISOLATION

Files:

- `tests/phase0/coordination_sqlite_proof.py`
- `tests/phase0/test_coordination_sqlite_proof.py`

The proof uses only stdlib `sqlite3`, `hashlib`, `hmac`, `json`, and `multiprocessing`, with databases under pytest temporary directories. It demonstrates:

- WAL plus `synchronous=FULL`;
- short `BEGIN IMMEDIATE` writes;
- atomic event + projection + outbox rollback;
- per-stream compare-and-swap conflict;
- resource-scoped monotonic fence rejection;
- atomic inbox + event + projection + outbox, including injected failure before the dedupe marker;
- outbox lease, fail, retry, stable message ID, and sent state;
- payload/hash/auth-tag tamper detection;
- deterministic in-memory projection rebuild;
- SQLite online backup and integrity/chain checks;
- subprocess contention with classified outcomes and no duplicate commit;
- immutable contract generations against update/delete/reuse;
- untouched sentinel paths.

Direct correction evidence: initial third-party output claimed the inbox proof was atomic, but direct review found an early commit. The helper was corrected to defer commit until the inbox marker and a regression test now injects failure at that boundary.

### 4.2 Named limits — not production ledger evidence

The disposable proof does not yet establish:

- authenticated production writer identity or server sequence/time;
- mandatory project/installation-scoped fencing for every privileged mutation;
- signed checkpoints, key rotation, or checkpoint rollback detection;
- persisted projection replacement and equivalence;
- poison-message termination or bounded retry policy;
- acknowledgement versus semantic completion separation;
- crash boundaries around external publish and unknown outcomes;
- concurrent generation amendment plus revocation-epoch advance;
- backup permissions, confidentiality, WAL/SHM operations, or atomic restore switching;
- throughput or filesystem portability.

Therefore it is evidence to start R2 TDD, not evidence to complete R3 or deploy a ledger.

## 5. Installed Hermes effect seam

### 5.1 VERIFIED control flow

- `/home/arty/.hermes/hermes-agent/model_tools.py:1021-1039` applies request middleware.
- `model_tools.py:1045-1088` calls `get_pre_tool_call_block_message()` and returns before dispatch when a structured block exists.
- `model_tools.py:1090-1102` applies ACP edit approval after the plugin block check.
- `model_tools.py:1134-1159` reaches `registry.dispatch()` only after those checks.
- `/home/arty/.hermes/hermes-agent/hermes_cli/plugins.py:1982-2029` recognizes `{"action": "block", "message": "..."}`.
- `model_tools.py:849-897` emits `post_tool_call` metadata only when a listener exists.

### 5.2 PROVEN IN ISOLATION

`tests/phase0/test_effect_boundary_proof.py` calls the installed `model_tools.handle_function_call()` with fake dispatch and isolated hook/middleware seams. It proves:

- a structured block prevents `registry.dispatch()`;
- blocked execution emits `status="blocked"` and `error_type="plugin_block"`;
- allowed execution dispatches once;
- task/session/tool-call/turn/API-request IDs and middleware trace reach the hook;
- duplicate observer invocation may be suppressed;
- hook exceptions are fail-open and allow dispatch;
- the proof itself causes no file, network, process, or live-tool effect.

Direct correction evidence: initial third-party output failed to patch the `has_hook("post_tool_call")` gate, so two claimed post-hook tests failed under independent execution. The fixture was corrected and the complete suite was rerun.

### 5.3 Shadow-only decision

The installed plugin hook is **observer/shadow infrastructure only** for v0.19. It is not the authoritative E2–E4 security boundary because both the hook invocation and callback failures can fall through.

## 6. Authoritative fail-closed boundary contract

Files:

- `tests/phase0/authorization_boundary_proof.py:13-125`
- `tests/phase0/test_authorization_boundary_proof.py:42-202`

The tests-only `authorize_then_dispatch()` proves feasibility of this mandatory production invariant:

> Every E2–E4 effect may reach its target dispatcher only after one authoritative decision has exactly bound principal, project, contract ID and generation, task, audience, target, effect class, revocation epoch, fencing epoch, and expiration. Missing, malformed, mismatched, stale, revoked, expired, unavailable, raised, or timed-out authorization denies or escalates and produces zero dispatches.

`skip_pre_tool_call_hook` is only an observer deduplication flag. The proof establishes that:

- the authoritative guard runs before dispatch;
- valid authority dispatches once;
- invalid authority with `skip_pre_tool_call_hook=True` still produces zero dispatches;
- exceptions, timeout-like errors, `None`, malformed decisions, every dimension mismatch, stale revocation/fence, revocation, and expiry fail closed.

### Production no-bypass invariant

When enforcement is implemented, E2–E4 targets must be reachable only through the authoritative boundary. Direct `model_tools.handle_function_call()` paths cannot be considered enforcement-authoritative. A caller-controlled skip flag must never bypass authorization; any internal authorization context used to avoid repeated work must be unforgeable, bound to the full decision, and single-use or otherwise replay-safe.

This Phase 0 helper is feasibility evidence only. Production integration and adversarial review remain R4/R6 gates.

## 7. Identity and recovery status

### Identity — GO WITH NAMED LIMITS

The authorization proof establishes the required binding shape, but no real identity root exists yet. Deferred to R4:

- Aether-issued PoP workload keys;
- project/session/runtime binding;
- key custody and rotation;
- online revocation;
- transferable/non-transferable capability semantics;
- replay protection and runtime evidence.

### Recovery — GO WITH NAMED LIMITS

SQLite mechanics establish deterministic data recovery feasibility. Deferred requirements:

- actual Olympus orphan/runtime reconciliation;
- unknown external-effect reconciliation before retry;
- no automatic E4 retry;
- signed checkpoint restore;
- process death and takeover evidence;
- semantic closure independent of transport/ACP completion.

## 8. Mandatory gates by roadmap phase

### Before R2 may start

Satisfied by this artifact and the executable proofs:

- Olympus lifecycle owner is identified with exact seams.
- Shadow hook and enforcement boundary are explicitly separated.
- The no-bypass/fail-closed invariant is executable in tests-only form.
- SQLite feasibility and limitations are recorded.
- R1 is classified `GO WITH NAMED LIMITS`, not unconditional GO.

### Before R3 may complete

Must be implemented and tested in production code:

1. project/installation-scoped mandatory fencing with no zero/default bypass;
2. authenticated writer metadata and server-assigned sequence/time;
3. append-only events, hash continuity, signed checkpoints, protected keys, and rollback detection;
4. persisted deterministic projection rebuild equivalence;
5. verified online backup/restore with permissions and WAL semantics;
6. crash-safe inbox/outbox, bounded retry, poison termination, and acknowledgement/completion separation;
7. atomic contract generation advance plus revocation/stale-message fencing;
8. repeated subprocess contention, writer-death recovery, and classified exhaustion.

### Before R4/R6 enforcement may complete

- real PoP identity and online revocation;
- authoritative boundary integrated immediately adjacent to every E2–E4 dispatcher;
- all rejection dimensions exercised against the real target equivalence class;
- no caller-controlled bypass;
- unknown outcomes reconcile before retry and E4 never auto-retries;
- Athena security PASS with no unresolved critical/high finding.

### Before R5 may complete

- production adapter calls only public Olympus lifecycle APIs;
- structural tests prove Harmonia/adapter do not own processes or sessions;
- two-project same-profile isolation and project-scoped shutdown are exercised;
- technical delivery/completion remains distinct from semantic completion.

### Before activation/release

Still prohibited without a user-present recovery gate:

- gateway restart/reconfiguration;
- live feature activation;
- production DB migration;
- live effects or pilot;
- merge, tag, or publication.

## 9. Executed validation

Final independent commands before security re-review:

```text
ruff check tests/phase0
All checks passed!

pytest tests/phase0 -q
43 passed in 0.67s

pytest -q
164 passed in 1.88s

git diff --check -- tests/phase0
PASS
```

Protected-path status was empty for:

- `home/config.yaml`
- `home/gateway_state.json`
- `src/olympus_v3/db.py`
- `src/olympus_v3/aether_db.py`
- `src/olympus_v3/server.py`
- `src/olympus_v3/acp_manager.py`

Gateway health during Phase 0 remained:

```text
ActiveState=active
SubState=running
MainPID=1239180
```

No live coordination runtime, effect, DB, service, or gateway action was executed.

## 10. Security QA history

- `qa_attempt=1`: **FAIL**.
  - Missing `PHASE_0_EVIDENCE.md`.
  - Fail-open plugin hook was not explicitly constrained to shadow mode.
  - No executable authoritative no-bypass boundary contract.
  - Olympus lifecycle seams were not in a canonical artifact.
- Corrections:
  - created this evidence artifact;
  - classified the plugin hook as shadow-only;
  - added and verified the fail-closed authorization boundary proof;
  - recorded exact Olympus owner/dispatch/teardown seams;
  - converted SQLite limitations into explicit R3 blockers.
- `qa_attempt=2`: **PASS**.
  - All attempt-1 blockers were resolved.
  - No Critical or High finding blocks R2 protocol/contract TDD.
  - Production identity, ledger, adapter, effect-enforcement, and recovery controls remain explicit R3–R7 gates.

## 11. Final Phase 0 verdict

**GO WITH NAMED LIMITS** for beginning R2 default-off protocol/contract TDD only.

This verdict is not authorization to enable a runtime, enforce effects through the fail-open hook, complete R3/R4/R5/R6 gates, touch the live gateway, run a pilot, merge, tag, or publish.
