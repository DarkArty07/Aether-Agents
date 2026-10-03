# External Implementer harness — design research

Decisions follow Spec Kit's research format (decision, rationale, alternatives). Claims are
labelled by how they were established (PD-41): **read** in code or documentation at a
stated revision, or **observed** by running a read-only command. Initial authoring
established no Claude Implementer run or pipeline result. The later bounded,
no-work-prompt readiness probes are separately attributed in §3.1.

## 1. Upstream method inspected

- **Spec Kit**, `github/spec-kit@7c54ef5d7140784a097d6c60bc4a778f0ac8d49f`,
  `templates/commands/plan.md:64-72,114-149` (read 2026-09-28, re-read 2026-09-30): the
  plan phase separates unknowns, research consolidated as *Decision / Rationale /
  Alternatives considered*, and Phase 1 interface contracts and quickstart. Aether reuses
  that separation: [`spec.md`](spec.md) holds intent and requirements, [`plan.md`](plan.md)
  the interfaces, [`quickstart.md`](quickstart.md) the runnable checks. The recurring Aether
  adaptation applies: where Spec Kit would ask a present human, the decision is already
  assigned to a role (owner decisions OD-1–OD-10; Morfeo's delegated decisions below;
  Supervisor/Implementer local freedom in plan §5).
- **Hermes worker lanes.** The upstream guide
  (<https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-worker-lanes>,
  read 2026-09-28) describes a lane as an executor that preserves Kanban lifecycle and
  audit, mentions external coding CLIs, and states that external integration is not yet a
  prepared path. PR NousResearch/hermes-agent#37659 (worker-lane registration) is **open
  and unmerged** at head `aa6e503ec0618d3c3536cec522e79d7102a5efe4`; issue #70547
  (configurable external spawners) is open (observed 2026-09-30 through the GitHub API).
  Neither is adopted: Aether must not depend on an unmerged upstream API or a
  downstream-only core change.

## 2. Current source evidence

Runtime: the selected rc17 release's `hermes-source` (maintained fork
`007cfb77676b6b024d2c0986f4585e6cfdcf18d6` according to its release lock; distribution
0.20.1). The tree has no `.git`; its identity comes from the lock, and its digest was not
revalidated for this design. Line numbers are inspection locators, not patch instructions.

| Fact | Locator |
| --- | --- |
| `HERMES_BIN` is the first resolution step for worker spawns; path-like values are used as-is. It is the only reader of `HERMES_BIN` in the runtime. | `hermes_cli/kanban_db.py:13811-13849` (read); repository-wide search (observed) |
| Worker spawn copies `dict(os.environ)`, sets `HERMES_PROFILE`, `HERMES_KANBAN_{TASK,RUN_ID,CLAIM_LOCK,DB,BOARD,WORKSPACE,GOAL_MODE,REVIEW_AFFINITY}` and related keys, and builds `hermes -p <profile> --cli … chat -q <prompt>` with optional `--resume`. | `kanban_db.py:13942-14265` (read) |
| Per-card pins travel as `--skills`, `-m`/`--provider`, `--reasoning`; `--toolsets` is profile-derived and always added when configured. | `kanban_db.py:14120-14146` (read) |
| Work claims (`claim_task`) and review claims (`claim_review_task`) both emit `claimed`; only the review claim records `source_status: "review"`. | `kanban_db.py:7468-7589`, `7622-7745` (read) |
| The kernel extends a claim while the worker PID lives unless the last heartbeat is older than one hour; stale-running detection also reclaims. | `kanban_db.py:7864` `release_stale_claims`, `11746` `detect_stale_running` (read) |
| Worker heartbeat helper keyed by the claim environment. | `tools/kanban_tools.py:377-430` (read) |
| Kanban tool identity is validated from `HERMES_KANBAN_TASK/RUN_ID/CLAIM_LOCK`. | `tools/kanban_tools.py:152-173` (read 2026-09-28) |
| Worker guidance constant and durable worker context builder. | `agent/prompt_builder.py:226` `KANBAN_GUIDANCE`; `kanban_db.py:14266` `build_worker_context` (read) |
| Stable worker exit codes: 75 rate limit/billing, 76 protocol. | `hermes_cli/kanban_exit_codes.py:11-12` (read) |
| The Morfeo gateway discovers plugins at startup; its Kanban watcher calls `dispatch_once`. | `gateway/run.py:12120-12136`; `gateway/kanban_watchers.py:2006` (read) |
| The gateway loads the profile `.env` with `override=True`. | `gateway/run.py:1893`; `hermes_cli/env_loader.py:470-500` (read) |

Local service (observed with `systemctl --user cat`): `hermes-gateway-morfeo.service` runs
`<runtime/current>/venv/bin/python -m hermes_cli.main --profile morfeo gateway run`; the
release environment ships console scripts (`aether`, `hermes`, …) in `venv/bin`.

Aether at `4bbf8ac261e5466fc72b1b3210f13eff5e76005d`:

| Fact | Locator |
| --- | --- |
| A1 #487 option B: Hermes owns the main gateway unit; Aether "does not add a drop-in". | `specs/001-aether-v1-productization/spec.md:9` |
| Final contracts: required keys, render, tolerant `key: json` parser, validation of required keys/type/status only. | `src/aether_agents/objective_contracts/store.py:176-192,656-735` |
| `prepare_handoff` binds the final bytes at `HEAD` and returns routing side data. | `store.py:911-1005` |
| Execution-board metadata creation and reuse validation. | `src/aether_agents/objective_contracts/hermes_plugin.py:137-283,396-480` |
| The objective-contract plugin registers only in the Morfeo profile. | `hermes_plugin.py:590-648` |
| Aether's TUI launcher scrubs an inherited `HERMES_BIN`. | `src/aether_agents/launcher.py:708-757` |
| Role → canonical skill map used by lifecycle. | `src/aether_agents/lifecycle.py:937-961` |
| PD-71 policy contract: stdin JSON, `pre_tool_call` only, `terminal`/`write_file`/`patch` inspection, durable-tool secret scan, truncation guard; block prints JSON and exits with its block code; role comes from the install location. | `policy/hooks/aether_pre_tool_policy.py:158-166,195-205,285-345` |
| Implementer approvals are off. | `src/aether_agents/resources/profiles/implementer/config.yaml:20-21` |
| Existing MCP bridge (Morfeo-specific) and optional-argument fix of #556. | `src/aether_agents/mcp/` (`morfeo_server.py`, `bridge.py`, `hermes_adapter.py`); PR #556 |
| R5 SC-501: each role runs as its own OS process under its own profile — the Claude attempt remains its own process tree bound to the Implementer identity. | `specs/r5-topology-and-isolation/spec.md:234` |

Usage sample (observed 2026-09-30, read-only over 104 local execution boards): 104
Implementer cards, 29 in goal-mode, 44 with pinned skills, 0 with a model or effort pin. An
earlier read of 187 boards (2026-09-28) found 118 of 408 Implementer cards in goal-mode.

## 3. Claude Code evidence

- **Binary 2.1.285** (`claude --help`, observed 2026-09-30): `--permission-mode` accepts
  `bypassPermissions`; `--permission-prompts none` means nobody answers prompts;
  `--input-format stream-json` works with `--print`; `--bare` skips settings/plugin hooks,
  plugin sync and OAuth/keychain reads. Flags used by plan §3.6 were checked against 2.1.284
  on 2026-09-28 (including `--append-system-prompt-file`, present in the binary although
  not in the help) and remain to be rechecked by the implementation on the exact version.
- **Headless** (<https://code.claude.com/docs/en/headless>, read 2026-09-28/29): `-p`
  starts in manual permission mode, so unanswered prompts deny; structured stream events
  include `system/init` and `system/api_retry` errors with categories such as
  `rate_limit`, `billing_error`, `authentication_failed`, `account_on_hold`; an MCP server
  may fail to load while the run still exits cleanly; the documentation announces that
  `--bare` may become the `-p` default.
- **Hooks and permissions** (<https://code.claude.com/docs/en/hooks>,
  <https://code.claude.com/docs/en/permissions>, read 2026-09-28): PreToolUse command
  hooks run in `bypassPermissions`; exit code 2 blocks before permission rules; other codes
  or a timeout do not block; an MCP-tool hook whose server errors is non-blocking.
- **Terms** (<https://code.claude.com/docs/en/legal-and-compliance>, read 2026-09-28): end
  users may run the unmodified binary with their own subscription; developers may not
  collect, store or broker Claude.ai credentials; Pro/Max limits assume ordinary individual
  use. Consequence: unmodified binary, no token handling by Aether, no `--bare`; quota use
  (including parallel attempts) is the owner's own plan usage and is documented.
- **Skills convention** (<https://agentskills.io/client-implementation/adding-skills-support.md>,
  read 2026-09-29): the specification defines the format; clients scan their own paths and
  optionally `.agents/skills`. Claude Code's native project path is `.claude/skills`.

### 3.1 Readiness premise resolved during execution (2026-09-30)

**Question:** collaboration #5 from EIH-C's same-card Supervisor review. Candidate
`8adac14dee851415161ef0669753bccfe3e3b350` checks `system/init`, and accepts an
absent/`ready` server status or any one prefixed tool. Supervisor's disposable probe
found all MCPs pending/needs-auth with no MCP tools at init. That does not prove the
worker unavailable, and the candidate's weaker checks do not prove the required
surface ready. EIH-C remains unaccepted.

**Upstream inspected directly:** `anthropics/claude-agent-sdk-python` at
`bbf09e3c11d3c5f2cfa2d9cf20af9b3abdfc1b4a` (GitHub API revision resolved, raw
files read, 2026-09-30):

- `src/claude_agent_sdk/_internal/query.py:309-363,784-802`: initialize the native
  streaming control protocol; `get_mcp_status` sends subtype `mcp_status`.
- `src/claude_agent_sdk/client.py:471-502` and `types.py:743-778`: the live MCP
  status response contains `mcpServers`, explicit status and `tools[].name`.
- `client.py:314-339`: setting permission mode is also a control operation. It was
  probed as corroboration, but is not needed by the selected readiness mechanism.

The SDK supplies the existing protocol, not a new dependency or execution harness.
The official Claude documentation requests returned HTTP 403; no documentation
content or behavior was invented in their place. Hermes' official worker-lane
page was readable and does not add an alternate role transport.

**Directly observed by Morfeo:** two bounded event-only probes of the installed
unmodified Claude Code **2.1.285**, binary SHA-256
`33dad1ec615a2e08cc78b494f05c110e49916de2c79d78ec8799ebf46b233d29`.
The command used exactly the plan §3.6 flags, a disposable MCP **fixture** named
`aether-worker` advertising only `probe_status`, added SessionStart/PreToolUse
settings, an empty probe plugin, disposable cwd and isolated Hermes/Aether state.
The normal Claude configuration stayed loaded; no forbidden isolation flag or
personal-config edit was used. The fixture is not the production worker surface.

- Probe 1: zero user messages; matching `initialize` success at 1.794 s, matching
  `mcp_status` success at 1.803 s with worker `status: "connected"` and
  `tools: [{"name": "probe_status", ...}]`; nonce matched. No `system/init`
  or model event occurred, so the original init-dependent oracle did **not** pass.
- Probe 2: no passive `system/init` during the first 3 s; matching `initialize`
  success at 3.089 s with nested data
  `current_permission_mode: "bypassPermissions"`; supplementary
  `set_permission_mode` success returned `mode: "bypassPermissions"`; matching
  `mcp_status` success at 3.092 s explicitly connected with `probe_status`.
  The SessionStart nonce matched the attempt; `permission_mode` in that hook's
  payload was null and is **not** a bypass oracle. Zero user messages and zero
  model events; the refined pre-prompt control/nonce oracle passed.

**Decision:** plan §3.7 uses the matched initialize response's effective mode,
matched live `mcp_status` with **all** required worker tools, and the same-settings
nonce. `system/init` is only later corroboration. This is a correction of the
readiness observational mechanism inside the delegated freedom, not a waiver or
change to EIH-08/AC7, fallback, effect authority or finalized contract terms.
Missing/unknown status or one available tool cannot open the gate.

**Limits and remaining work:** these probes prove a deterministic CLI control
path before any work prompt; they do not prove actual native worker MCP readiness,
PD-71 tool evaluation (no tools were called), unit correctness, EIH-12, installed
availability or agent behavior. Supervisor returns the narrow gate/evidence
correction through EIH-C's existing review lane and preserves its review budget.
The isolated real work attempt and the repository gates remain pending. Both
probe subprocesses were reaped and their disposable scopes removed; the sanitized
observations are retained here, not raw user configuration or transcripts.

**Supplementary originating-session check (Morfeo TUI):** while the scheduled
follow-up produced the decision and the two observations above, the originating
session independently read the same exact SDK sources and installed binary, then
performed two additional bounded control-only fixture probes. These used a fixture
tool named `readiness_probe`, not the production worker. Matching initialize replies
succeeded; live `mcp_status` reported the fixture worker explicitly connected with
that tool; the SessionStart nonce matched the session. The second probe corroborated
`set_permission_mode` with a success response containing `mode: "bypassPermissions"`.
No user frames or model-message events were sent/observed, and no pre-prompt
`system/init` appeared. Both owned process groups had no live members after cleanup;
their temporary inputs were retired. Raw personal MCP configuration and stderr were
not printed or retained.

This check supports the control-status premise and does not replace the selected
initialize-mode observable, require a permission setter, prove the full worker
surface/PD-71 evaluation, or count as the isolated EIH-12 work run. The originating
session successfully fetched the official headless documentation; that does not
retroactively change the scheduled producer's HTTP-403 limitation recorded above.

### 3.2 Turn end and failure-signal fields resolved at integration (2026-10-03)

**Observed:** isolated run 26 on Claude Code 2.1.288 passed the pre-prompt gate and
received the work prompt; the owner's then-default model, reachable only through a
local router absent from the attempt environment, returned `model_not_found`/404 at the
first model call. The CLI then stayed alive without activity for more than two hours,
so no classification, receipt, comment or fallback happened. The adapter never ended
Claude's input and read failure fields the CLI does not emit.

**Upstream inspected directly** (2026-10-03): the official TypeScript Agent SDK
`@anthropic-ai/claude-agent-sdk` 0.3.258 as installed locally.

- `sdk.mjs`, `Query.readMessages`: on the first `result` of a single-turn query it logs
  "First result received for single-turn query, closing stdin" and calls
  `transport.endInput()`. Streaming input ends the input once its iterable is exhausted,
  after the first result when the host has bidirectional needs.
- `sdk.d.ts`: `SDKAPIRetryMessage.error` is an `SDKAssistantMessageError`
  (`authentication_failed`, `oauth_org_not_allowed`, `account_on_hold`,
  `billing_error`, `rate_limit`, `overloaded`, `invalid_request`, `model_not_found`,
  `server_error`, `unknown`, `max_output_tokens`). `SDKResultSuccess` and
  `SDKResultError` carry `subtype` and `is_error`; neither has a `status` field.
- Official headless documentation (<https://code.claude.com/docs/en/headless>): the
  `system/api_retry` table names the `error` field and its categories, and a failure
  inside a run is printed as the result.

**Decision (plan §3.11):** end Claude's input after the first `result`, read stdout
through a line queue, drain stderr, and classify from `api_retry.error`, the assistant
`error` and `result.is_error`/`subtype`. The earlier fixtures emitted an invented
`error_category` and a result `status`, so the focused tests proved self-consistency
only; they now use the documented shapes, and the stubs keep reading input after their
result like the real CLI.

**Limits:** the SDK is inspected as the reference protocol client, not added as a
dependency. A fresh isolated run on the corrected candidate is recorded in
[evidence/EIH-INT.md](evidence/EIH-INT.md); it proves one working path, not agent
behavior or installed availability.

## 4. Decisions

The readiness assumption in the original authoring row below was resolved during
execution; the current mechanism is plan §3.7, with the direct evidence in §3 above.
The accepted invariants and effect authority are unchanged.

| Decision | Rationale | Alternatives rejected |
| --- | --- | --- |
| Deliver `HERMES_BIN` from the Morfeo-profile Aether plugin, in-process, to its own release's launcher (OD-9). | Uses the dispatcher's documented override, reaches the real gateway dispatch path, keeps Hermes' unit ownership and the credential file untouched; a missing launcher leaves Hermes' default. | systemd drop-in (contradicts A1 #487); profile `.env` (credential file); PR #37659 lanes (unmerged upstream); `spawn_fn` injection (test seam; profile filters run before it); monkeypatch or second scheduler (forbidden). |
| Optional `implementer_harness` front-matter key; board projection. | Closed-set, structured, immutable per version; earlier readers tolerate it and fall back to Hermes, which OD-3 accepts. | New artifact type (unneeded); parsing prose (forbidden); global or profile setting (would affect concurrent contracts). |
| Stateless per-attempt fallback by `execv` inside the claim (OD-3). | Same PID, claim and deadline; avoids the per-task cooldown that a quota exit would impose on Hermes too (`kanban_db.py:12048-12233`); no invented task runs. | New Kanban attempt after exit 75; sticky per-unit fallback; circuit breaker or failure memory (owner rejected global state). |
| Reviews stay on Hermes (delegated). | Assumed few; keeps review affinity and Supervisor continuity without extra work. Invalidated if Implementer-assigned reviews become a significant share. | Routing by column or by the card's previous executor. |
| Goal-mode stays on Hermes (OD-6). | Claude's `--max-turns` is not Hermes' judged loop. | Reusing `run_kanban_goal_loop` callbacks now (deferred with goal-mode's future). |
| Model/effort pins keep the card on Hermes (delegated). | A Hermes model pin cannot be honored by Claude; silently dropping it would change the requested execution. Zero observed pins make the cost negligible. | Ignoring pins; mapping Hermes models to Claude models. |
| Per-attempt skills plugin from the role map (OD-5). | Single source; read-only; no mixing with project or personal sessions. | Writing `.claude/skills`, `.agents/skills`, `~/.claude/skills` or `~/.agents/skills`. |
| User's Claude configuration untouched (OD-4). | Owner decision; Aether adds only its minimum. | `--strict-mcp-config`, `--setting-sources`, `CLAUDE_CONFIG_DIR`, `--bare` (also disables OAuth). |
| `bypassPermissions` + `--permission-prompts none`, verified per run (OD-2). | Matches Hermes Implementer approvals off; headless default would deny. | `--restricted` (rejects bypass); `dontAsk`; relying on user settings. |
| PD-71 via a fail-closed PreToolUse command-hook adapter over the unchanged policy. | Only exit 2 blocks in Claude; MCP tool hooks are non-blocking on error. | MCP-side hooks only; a reimplemented Claude-specific policy. |
| Readiness by stream-json input gating plus a `SessionStart` nonce (assumed). | Keeps the work prompt away from the model until MCP, bypass and hook are proven. Must be confirmed on the exact version; otherwise a stop condition. | Trusting exit 0 or the absence of errors. |
| A2A remains unused (R6 FR-606 reconsidered). | The executor runs on the board's host, is spawned per attempt by the native dispatcher and needs fresh context; A2A would add a server per peer and route into live sessions. The board stays the record (FR-607). | A2A as the Claude transport. |

## 5. Transfer from local exploration

The design history (2026-09-28/29), including superseded hypotheses (sticky fallback,
goal-mode callbacks, a new artifact type, drop-in delivery), is preserved in the local
continuity note `.aether/observations/harness-agnostic-aether.md`. That note is local,
ignored and non-authoritative; every decision this objective relies on is restated here,
in [`spec.md`](spec.md) or in [`plan.md`](plan.md). Separately tracked defects found during
exploration (#557 MCP memory limits, #558 bootstrap size, #559 knowledge-tool
qualification, #560 doctor revalidation reason, #561 misleading gateway-unit comment) are
not part of this objective.

## 6. Design self-check

Cold read, receiver's view: the shared identifiers, eligibility, fallback triggers,
fail-closed behavior, compatibility and verification are fixed. Remaining freedom is local
(names, internal structure, readiness mechanics within the invariant, heartbeat rate,
receipt layout). The material unverified assumptions — the exact readiness event sequence
on 2.1.285 and the hook's coexistence with the user's own hooks — are bounded by explicit
stop conditions in plan §7 and do not need an owner decision unless they fail. This is an
author self-check, not independent review.
