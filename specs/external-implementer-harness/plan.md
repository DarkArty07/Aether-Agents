# Technical plan: opt-in Claude Code executor for Implementer work

**Owning intent:** [spec.md](spec.md), OD-1–OD-10 and EIH-01–EIH-12

**Inspected source:** Aether `main` at `4bbf8ac261e5466fc72b1b3210f13eff5e76005d` and the
selected rc17 runtime's Hermes (maintained fork `007cfb77676b6b024d2c0986f4585e6cfdcf18d6`
per its release lock, distribution 0.20.1); Claude Code 2.1.285. Exact locators and
evidence are in [research.md](research.md).

**Disposition:** design for one Objective Contract; implementation authorized; no
release or activation

## 1. Route and boundaries

One Objective Contract carries the increment. Its parts share interfaces (contract field →
board metadata → launcher → adapter → MCP/hook/receipt) and together produce one
acceptable outcome: an opt-in contract whose Implementer work attempts run on Claude Code
with a stateless Hermes fallback, while the default path stays identical. Independent
review has concrete value here: default-path identity, fail-closed PD-71, single-writer
fallback and closed-set validation are easy to get subtly wrong. Supervisor owns the unit
breakdown and `tasks.md`. Natural seams — not a prescribed breakdown — are: contract
selection and board projection; gateway override and launcher routing; Claude adapter,
readiness, process lifecycle, outcome classification and receipts; worker MCP server;
PD-71 hook adapter; context and skills; guidance and documentation.

The artifact is reviewed source merged through the normal GitHub path. It is not a release
candidate, managed update or installed activation (OD-8). Compatibility conclusions:
`release_impact=minor` (additive, opt-in, tolerated by earlier readers),
`release_action=defer`, `release_channel=none`.

## 2. Architecture

```text
Owner → Morfeo ── objective_contract begin(implementer_harness="claude-code")
                        │ final front matter: implementer_harness: "claude-code"
                        ▼
              prepare_handoff → execution board.json: aether_implementer_harness
                        │
Supervisor (Hermes, flow session) decomposes → Implementer cards on that board
                        │
Morfeo gateway dispatcher (native, unchanged) claims a card, builds argv/env
   HERMES_BIN = <this release>/aether-kanban-worker   (set by the Aether plugin)
                        ▼
aether-kanban-worker (no LLM) ── not eligible / any error ──► exec hermes (pre-change resolution)
                        │ eligible
                        ▼
claude -p … (official binary, user's config + Aether additions, bypass, stream-json)
   ├─ PreToolUse hook  → adapter → unchanged PD-71 policy (fail-closed)
   ├─ MCP "aether-worker" → native Kanban worker tools + knowledge/memory (attempt identity)
   └─ skills plugin dir + appended Implementer context
                        │ result: native Kanban transition only
                        ▼
Supervisor reviews on Hermes; unavailability → same claim continues on Hermes (exec)
```

No scheduler, parallel board, second dispatcher, Hermes core change, reformulating Hermes
agent or REST-style Claude provider is added. The launcher controls only a worker that
Kanban has already claimed.

## 3. Interfaces and decisions

### 3.1 Fixed shared identifiers

| Identifier | Value | Owner of meaning |
| --- | --- | --- |
| Tool parameter | `implementer_harness`, enum `hermes` \| `claude-code` | EIH-02 |
| Final contract front-matter key | `implementer_harness: "claude-code"` (absent ⇒ Hermes) | EIH-02 |
| Execution-board metadata key | `aether_implementer_harness: "claude-code"` (absent ⇒ Hermes) | EIH-02 |
| Worker launcher console script | `aether-kanban-worker` | EIH-03 |
| Worker MCP server name | `aether-worker` (Claude tool names `mcp__aether-worker__<tool>`) | EIH-06 |
| Executor receipt schema | `aether.harness-receipt.v1` | EIH-09 |
| Kanban comment first-line prefix | `aether-executor:` | EIH-09 |

The closed set of external harnesses is `claude-code`. Adding a harness later extends that
set and adds an adapter behind the same launcher seam; it does not change these meanings.

### 3.2 Contract selection (EIH-01, EIH-02)

- `objective_contract` gains the optional parameter `implementer_harness`, accepted only by
  `begin` and `supersede`; any other action receiving it is rejected rather than ignored.
  `begin`: omitted or `hermes` ⇒ no selection. `supersede`: omitted ⇒ inherit the superseded
  version's selection; `hermes` ⇒ clear; `claude-code` ⇒ set. `show` reports it.
- The draft stores the selection only when set. The final renderer emits
  `implementer_harness: "claude-code"` only when set, so a contract without a selection
  renders exactly today's bytes. Final validation rejects any other value with the existing
  invalid-final error class; an unknown value is never treated as absent.
- `prepare_handoff` passes the final contract's selection to the execution-board
  provisioner. The envelope, root card and child bodies carry no harness text.
- Morfeo sets `claude-code` only on the owner's explicit request when starting the contract
  (OD-1); prose in sections never selects anything.

**Compatibility (verified by inspection):** the rc17 reader parses every `key: json`
front-matter line and only requires the known keys, artifact type and final status
(`store.py:688-735`). An earlier release therefore accepts a selected contract and runs it
entirely on Hermes — the always-permitted fallback. No new artifact type is needed.

### 3.3 Execution-board projection (EIH-02)

- On exclusive creation, execution-board metadata gains `aether_implementer_harness:
  "claude-code"` only when the contract selects it (`hermes_plugin.py:137-205`).
- On reuse, validation additionally requires the stored value to equal the contract's
  selection, both absent included, and otherwise fails with the existing identity-conflict
  error (`hermes_plugin.py:208-283`). A board created by an earlier release for an
  unselected contract remains valid. Contract bytes are immutable per version, so the
  selection of a version never changes.

### 3.4 Gateway override (EIH-03, OD-9)

- The package declares the console script `aether-kanban-worker`, installed into each
  release environment next to its `hermes` script.
- In `aether_agents.objective_contracts.hermes_plugin.register`, after the existing Morfeo
  profile check, the plugin sets `os.environ["HERMES_BIN"]` to the absolute path of the
  launcher in the **running release's own scripts directory**, resolved so that it does not
  pass through the `runtime/current` selector (a running gateway must never exec another
  release's launcher). It sets the value only when that path is a regular executable file;
  otherwise it leaves the environment unchanged. Repeated registration is idempotent.
- The dispatching gateway is the Morfeo profile gateway, which discovers plugins at
  startup before dispatching; `_resolve_hermes_argv` reads `HERMES_BIN` at every spawn and
  the worker inherits `dict(os.environ)`. Only the worker spawn path reads `HERMES_BIN`.
- Aether's launcher continues to scrub an inherited `HERMES_BIN` (`launcher.py:708-757`);
  the managed value is introduced after that, in-process. The Hermes-owned gateway unit,
  its drop-ins and the credential `.env` are not touched.

### 3.5 Launcher routing (EIH-03, EIH-10)

The launcher is invoked as `HERMES_BIN <dispatcher argv…>`. An attempt is **eligible** for
Claude Code only when all of the following hold; the decision reads environment, argv,
execution-board metadata and — read-only — the board database:

1. `HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, `HERMES_KANBAN_CLAIM_LOCK`,
   `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`, `HERMES_KANBAN_WORKSPACE` and `HERMES_PROFILE`
   are present, and the workspace directory exists.
2. `HERMES_PROFILE` is the canonical `implementer` profile.
3. The metadata of board `HERMES_KANBAN_BOARD` — the `board.json` in the same canonical
   board directory as `HERMES_KANBAN_DB`, rejecting symlinks and redirection as the
   provisioner does — carries an Aether contract identity and
   `aether_implementer_harness == "claude-code"`.
4. `HERMES_KANBAN_GOAL_MODE` is not `1` (OD-6).
5. The attempt is a **work** claim: the current run's latest `claimed` event does not carry
   `source_status: "review"` (`claim_review_task` records it; `claim_task` does not),
   `HERMES_KANBAN_REVIEW_AFFINITY` is unset and argv has no `--resume`.
   The event must exist for this exact `HERMES_KANBAN_RUN_ID`; if its row is absent,
   eligibility is false. A claim from another run cannot substitute for current-run
   evidence. This restates the current-attempt condition and the Hermes-on-uncertainty
   invariant; it is not an additional acceptance gate.
6. The card pins no Hermes model or effort (`-m`, `--provider`, `--reasoning` in argv).
   `--skills` pins are honored (§3.8); the profile-derived `--toolsets` argument is always
   present and does not affect eligibility.
7. A `claude` executable resolves on `PATH`.

Otherwise — and on any exception while deciding, including a missing or corrupt board
file or an unreadable database — the launcher replaces itself (`execv`) with the Hermes
entry point the dispatcher would have resolved **without** the override: `hermes` on the
inherited `PATH`, else the interpreter's `hermes_cli.main` module form
(`kanban_db.py:13846-13849`), with the unchanged argv tail and environment. It never
re-reads `HERMES_BIN`. This keeps the default path equal to today's, including during a
release switch. Uncertainty always resolves to Hermes. Because every worker spawn now
passes through the launcher, this pass-through must be the simplest and most heavily
tested path.

**Current-source clarification, 2026-09-30 (Morfeo):** a disposable helper probe of
EIH-B candidate `af9ab4ad220f3bc0537413a7eb3547a557a868d2` found that
`_check_claimed_event_not_review` accepts a work claim from run 10 when queried for
missing run 11. That is a condition-5 defect, not an optional compatibility residual:
the expected result is ineligible/Hermes. Supervisor resolves the bounded correction
and its focused regression through the existing integration/rework lane, preserving
the accepted unit commit and evidence. No contract-term change, completed-card mutation,
new objective or broad verification campaign is required.

### 3.6 Claude Code invocation (EIH-04, OD-2, OD-4)

With `cwd = HERMES_KANBAN_WORKSPACE` and the launcher's environment:

```text
claude -p --input-format stream-json --output-format stream-json --verbose
  --permission-mode bypassPermissions --permission-prompts none
  --session-id <new UUID per attempt>
  --append-system-prompt-file <attempt context>
  --mcp-config <attempt MCP config>
  --settings <attempt hook settings>
  --plugin-dir <attempt skills plugin>
```

`stream-json` output requires `--verbose`; `--permission-prompts none` makes anything that
would still prompt deny instead of waiting for a human. Aether's settings and MCP config
are **added** to the user's: never `--bare` (it skips hooks/plugins and OAuth),
`--strict-mcp-config`, `--setting-sources`, `CLAUDE_CONFIG_DIR`, `--model`, `-w/--worktree`,
`--continue` or `--resume`. The binary is not modified, and Aether never reads, copies or
stores Claude credentials. The Claude version is recorded per attempt. Should a future
version make bare mode the `-p` default, readiness fails (§3.7) and the attempt falls back
until an explicit non-bare option is added.

### 3.7 Readiness gate (EIH-08, EIH-10)

The work prompt is written to Claude's input only after positive evidence of all
three invariants: effective bypass mode, the connected worker MCP with its required
tools, and the active PD-71 settings source. On Claude Code 2.1.285 the deterministic
pre-prompt observable is the CLI's native stream-json **control protocol**, not the
initial `system/init` tool snapshot:

1. Send a `control_request` with a unique `request_id` and
   `request: {"subtype": "initialize", "hooks": null}`. Accept only the matching
   `control_response.response` with `subtype: "success"` and
   `response.current_permission_mode == "bypassPermissions"`. `hooks: null` adds no
   SDK callback hooks; the command hooks and the user's configuration remain loaded.
2. Send `control_request` messages with `request: {"subtype": "mcp_status"}` within
   the existing bounded readiness deadline. Accept only a matching success response
   whose `response.mcpServers` includes `name: "aether-worker"`, explicit
   `status: "connected"`, and `tools[].name` containing **every** required tool from
   the derived worker surface (§3.9) for this attempt. The required set is nonempty;
   its discovery/representation remains local implementation freedom. An absent
   status, `pending`, another server, or one matching tool is not positive evidence.
3. Confirm the existing `SessionStart` nonce for this attempt, written by the same
   per-attempt settings source that registers the blocking PD-71 `PreToolUse` hook.
4. Only then send the first user work message (§3.8). No warm-up user prompt, tool
   call, model inference or SDK dependency is needed to establish readiness.

Readiness has a bounded timeout. In the control responses above, the outer
`event.response` carries `subtype` and the matching `request_id`; the success data
are at `event.response.response` (effective mode or `mcpServers`). An error,
missing field, unmatched response or unmet invariant never opens the prompt gate;
failure terminates the Claude process group and falls back (§3.11). A later
`system/init` is corroborating run evidence,
not a substitute for the positive pre-prompt handshake. Invocation flags, PD-71,
user configuration, fallback and single-writer rules are unchanged.

The live status response may also contain other servers' configuration, headers or
environment fields. Consume only the worker's status/tool-name projection needed for
the gate; do not copy or persist raw control replies or unrelated configuration in
receipts, evidence or the bounded failure stream tail. This preserves EIH-09's existing
no-secrets boundary for the corrected observable, not a new reporting deliverable.

**Resolved assumption, 2026-09-30 (Morfeo, collaboration #5):** a disposable
no-user-message probe of the exact binary returned successful `initialize` with
`current_permission_mode: "bypassPermissions"` and `mcp_status` with the fixture
worker explicitly connected and its tool listed. The nonce matched; no model
message or `system/init` occurred before the gate. This resolves the observational
premise, not AC7/AC10 or EIH-C implementation acceptance. Details and limits are in
[research.md](research.md) §3. The unaccepted candidate `8adac14d` must be corrected
and its mocked readiness evidence reconciled by the existing review lane. The
invariant in EIH-08/AC7 and contract terms do not change. If this protocol cannot
prove the **actual** worker surface before its work prompt, stop (§7); do not weaken
the gate.

**Current review reconciliation, 2026-09-30 (Morfeo):** EIH-C's first ordinary
review return substituted a hand-picked tool list containing `memory`,
`session_search`, `skills_list`, `skill_view`, `todo` and `terminal`. That list
contradicts §3.9 and AC5/EIH-06; it is not an authorized worker surface or a new
acceptance requirement. The gate requires every tool in the nonempty surface
actually derived for this attempt, while the server itself remains limited to
§3.9. A previously observed tool list is evidence, not a static replacement for
that derivation. The correlated `initialize` effective-mode check, MCP check,
nonce and control-reply privacy rule above all remain applicable.

The same return cited test and fixture paths absent from candidate `8adac14d`.
Its actual readiness evidence is `evidence/EIH-C.md` §4, and its focused tests
are `tests/test_claude_code_adapter.py`, `tests/test_worker_mcp_server.py` and
`tests/test_pd71_claude_hook.py`. Reconcile the existing evidence and affected
checks under quickstart §1, not a fabricated fixture or additional suite. These
paths identify the inspected candidate; they do not remove §5's local naming
freedom. Supervisor clarifies this same return and Implementer continues the
already-authorized correction; the return remains 1 of 2, with no new card,
budget reset, contract-term change or acceptance.

### 3.8 Context and skills (EIH-05, OD-5)

- **Appended context file:** the Implementer `SOUL.md` and `implementation-evidence`
  SKILL from the running release's resources; `KANBAN_GUIDANCE` imported at run time from
  the executing Hermes (`agent/prompt_builder.py`), never copied into Aether source; the
  task-pinned skills from `--skills`; a short attempt header (task, workspace, delivery only
  through Kanban tools); and a tool-equivalence table mapping Hermes tool names used by the
  SOUL, skills and guidance to Claude's (`terminal`→`Bash`, `read_file`→`Read`,
  `write_file`→`Write`, `patch`→`Edit`/`MultiEdit`, `search_files`→`Grep`/`Glob`,
  `todo`→`TodoWrite`, `delegate_task`→Claude's own subagents within the same authority,
  Kanban/knowledge/memory tools→`mcp__aether-worker__<tool>`; tools without an equivalent
  are named as unavailable).
- **First user message:** `Work Aether Kanban task <id>.` followed by the task's durable
  worker context from `build_worker_context` over a read-only board connection.
- **Skills plugin:** generated per attempt (`.claude-plugin/plugin.json` plus
  `skills/<name>/SKILL.md`) from exactly the Implementer role's canonical skill set in
  lifecycle's role map (`lifecycle.py:937-961`) at the running release. Nothing is written
  into the project (`.claude/skills`, `.agents/skills`) or the user's personal skill
  directories. The map stays the single source for every harness.

### 3.9 Worker MCP server (EIH-06)

- An internal stdio server module run with the release interpreter, launched by Claude
  from the per-attempt MCP config with the attempt identity environment (implementer
  `HERMES_HOME` and `HERMES_PROFILE`; `HERMES_KANBAN_TASK/RUN_ID/CLAIM_LOCK/DB/BOARD/
  WORKSPACE` and related variables).
- Surface derived at startup, not hand-picked: the Kanban tools the Hermes tool registry
  grants a dispatched Implementer worker under that identity, plus `project_knowledge` and
  `work_memory` when the Implementer profile enables them. No file, terminal, web, memory,
  session, skills, delegation, todo or Morfeo tools. The exposed list is recorded in
  evidence.
- Calls delegate to the native handlers, which keep their task/run/claim identity checks
  (`tools/kanban_tools.py`). Only supplied arguments are forwarded (the #556 bridge
  behavior); results are returned faithfully; no bootstrap payload. Reuse the existing MCP
  bridge pieces where they fit; do not hand Implementer the Morfeo server or identity.

### 3.10 PD-71 hook adapter (EIH-07)

- A `PreToolUse` command hook with matcher `*`, run with the release interpreter, with an
  internal deadline shorter than Claude's hook timeout.
- It translates Claude's input into the policy's existing contract
  (`{"hook_event_name": "pre_tool_call", "tool_name", "tool_input"}`): `Bash`→`terminal`
  (`command`); `Write`→`write_file` (path, content); `Edit`/`MultiEdit`/`NotebookEdit`→
  `patch` (path and edit text); `mcp__aether-worker__<tool>`→`<tool>` with its arguments;
  every other tool keeps its name and input so the policy's generic checks still apply.
- It evaluates the translated payload with the **unchanged** policy exactly as installed for
  the Implementer profile (`policy/hooks/aether_pre_tool_policy.py`; role from its install
  location). No policy logic is forked or reimplemented.
- Allow ⇒ exit 0. Policy block ⇒ exit 2 with the policy reason on stderr. Unparsable
  input, missing policy, adapter error or internal timeout ⇒ exit 2. In Claude only exit 2
  blocks; any other code or a hook timeout would not, which is why the adapter itself must
  fail closed. Each call's `permission_mode` is recorded in the bounded attempt log.

### 3.11 Process lifecycle and outcome (EIH-08, EIH-09, EIH-10)

- The launcher remains the PID the kernel supervises for the whole attempt. Claude runs in
  a new session/process group with a Linux parent-death signal; SIGTERM/SIGINT to the
  launcher are forwarded to the group. After Claude ends, the launcher terminates remaining
  group members (TERM, then KILL after a grace period) and waits until the group is empty.
- **Single writer:** before any fallback the launcher also confirms that no process other
  than itself has a working directory inside the attempt's worktree. If a writer may
  survive, it does not fall back; it exits through the kernel's ordinary failure path.
- **Heartbeat:** `heartbeat_current_worker_from_env()` on real stream events, rate-limited
  (at most once per 30 s). A single silent tool call longer than the kernel's one-hour
  heartbeat window is a disclosed limit, not hidden with a timer.
- **Classification** after Claude ends, reading the board read-only:

| Observed | Action |
| --- | --- |
| This run produced a native transition (review requested, completed, blocked) | exit 0 |
| Launcher received SIGTERM (kernel timeout/cancel) | propagate, wait, exit 143; no fallback |
| Task cancelled, claim lost/changed or already terminal | exit without fallback |
| Readiness failed (MCP, hook, bypass) | fallback |
| Structured auth/billing/rate-limit signal (`system/api_retry` error categories such as `authentication_failed`, `billing_error`, `rate_limit`, `account_on_hold`, or the equivalent terminal result error) and no transition | fallback |
| Non-zero exit, signal death or error result, and no transition | fallback |
| Clean success result and no transition | exit 76 (kernel protocol path); no fallback |

- PD-71 denials, red tests, review returns and difficulty are not classifications: Claude
  keeps working and its final state is judged as above. Signals are read from structured
  events and exit status, never from regular expressions over tool output; unknown signals
  are recorded as unknown.
- **Fallback:** record the cause, verify the process group is gone and the single-writer
  check passes, confirm the claim and task are still this attempt's, then `execv` the same
  pass-through Hermes entry as §3.5 with the original argv tail and environment. Hermes
  inherits the same claim, PID and remaining deadline, and reads the worktree and durable
  card context as any later attempt would; no Claude transcript is transferred and no
  summary is invented. At most one substitution per attempt; no ping-pong and no failure
  memory across attempts.

### 3.12 Receipts and local state (EIH-09)

- Receipt `aether.harness-receipt.v1` in Aether-managed local state (XDG state root,
  scoped by board/task/run): harness, harness version, session id, board, task, run, start
  and end UTC, readiness summary, outcome, cause, fallback flag and exit status. No prompt
  text, secrets or credentials.
- One native `kanban_comment` from the attempt identity whose first line starts with
  `aether-executor: claude-code <version> session=<id> outcome=<outcome>` (plus
  `cause=<cause>` when applicable).
- Transient inputs (context file, MCP config containing the claim lock, settings, plugin
  directory, nonce) are removed when the attempt ends; a bounded stream tail (≤256 KiB) is
  kept only for failed or fallback attempts.
- Claude session ids are external identifiers. They are never inserted into Hermes'
  SessionDB, and observation discloses the missing transcript/token coverage instead of
  filling it (`observation/capture/hermes_plugin.py` validates native sessions).

### 3.13 Minimum requirements and guidance (EIH-11, OD-1, OD-4)

User documentation states the minimum requirements: Claude Code installed and logged in by
the user; it must be able to work unattended (a user hook or plugin that requires human
interaction is the user's to adjust); Aether adds its context, skills, MCP server and hook
only for the run; `disableBypassPermissionsMode` or a missing binary makes attempts fall
back to Hermes; attempts, including parallel ones, consume the user's own plan; the
default is Hermes. Morfeo's SOUL and `objective-contract-design` carry OD-1. Reconcile
`docs/guides/expected-behavior.md`, the applicable current page, `docs/capabilities.toml`
with its generated reference, and `CHANGELOG.md` (Unreleased) per `CONTRIBUTING.md`.

## 4. Invariants

- No selection ⇒ identical contract/board bytes and the same Hermes execution as today.
- Routing uncertainty ⇒ Hermes; PD-71 uncertainty ⇒ block.
- At most one writer per worktree at any time.
- Delivery exists only as native Kanban transitions by the attempt identity.
- No Claude credential access; no modification of the user's harness configuration.
- No state carried between attempts other than receipts.

## 5. Local freedom

Implementer and Supervisor choose module and file names (other than §3.1), internal
functions, the exact readiness mechanism within §3.7's invariant, heartbeat rate within
§3.11, the receipt path layout under Aether's state root and the wording of the
equivalence table. They may not change a §3.1 identifier, eligibility (§3.5), fallback
triggers (§3.11), the fail-closed rule or the out-of-scope list without returning to
Morfeo. No new third-party runtime dependency is needed or authorized: the standard
library and the release's existing `mcp` extra (A1 release-lock schema 5) suffice.

## 6. Testing standard and acceptance mapping

The owner chose minimal verification (OD-7); the project standard in
`CONTRIBUTING.md` still applies to touched code. Use focused tests while iterating, then
the repository's integrated gate before handoff and the normal required PR checks. Add
tests only for the boundaries this change introduces; no comparisons, benchmarks or agent
campaigns. [quickstart.md](quickstart.md) carries the runnable commands.

| Criterion | Decisive scenario/result | Evidence |
| --- | --- | --- |
| EIH-01 | Unselected contract renders byte-identical to the pre-change renderer; unselected board metadata unchanged; launcher pass-through resolves the pre-change Hermes entry and reproduces argv and environment exactly for every non-eligible case, including board/database read failures. | Focused store/board/launcher tests with a stub `hermes`. |
| EIH-02 | `begin`/`supersede` semantics; unknown value rejected; projection on creation; reuse mismatch conflicts; rc17-style parse of a selected contract succeeds. | Focused tests. |
| EIH-03 | Plugin sets `HERMES_BIN` only with a valid release launcher; each §3.5 condition independently forces Hermes; decision errors pass through. | Focused tests. |
| EIH-04/05 | Built command matches §3.6 and never includes forbidden flags; context contains SOUL, evidence skill, runtime guidance, pinned skills and table; plugin holds exactly the role skill set; nothing written to project or personal skill paths. | Focused tests plus the isolated real run. |
| EIH-06 | Server surface equals the derived worker set; identity-bound; only supplied arguments forwarded; foreign task rejected by the native checks. | Focused tests. |
| EIH-07 | Claude-shaped payloads map correctly; policy blocks surface as exit 2; malformed input, missing policy and timeout exit 2. | Focused tests. |
| EIH-08/10 | With a stub `claude` emitting canned stream-json: readiness failures, auth/rate-limit/error/crash fall back once via exec; clean exit without delivery exits 76; cancellation, lost claim and surviving writer never fall back; process group is empty before fallback. | Focused tests. |
| EIH-09 | Receipt fields and comment prefix; transient inputs removed; no Hermes session row created. | Focused tests plus the isolated real run. |
| EIH-11 | SOUL/skill text states OD-1; documentation checks pass. | Resource checks and `check_documentation.py`. |
| EIH-12 | One isolated real run: a disposable Implementer card executed by real Claude Code reaches review through the real Kanban tools, with readiness evidence, hook invocation and receipt. | Quickstart §3 record. |

Resource and focused tests show deterministic source behavior. The isolated run shows the
path works once; neither claims installed availability or broad agent-behavior quality.

**Clarificación del oráculo integrado, 2026-10-03 (Morfeo):** en el candidato
`a82650fb24e630c2c82521b1b8a67f32ba186593`, la prueba
`test_import_boundary_is_static_and_manager_modules_import_without_hermes`
(`tests/test_observation_cli_plugin.py:1978–2015`) enumera tres importadores
Hermes anteriores y no contempla los componentes de ejecución de #563. La
frontera normativa de `DESIGN.md` PD-69 y
`specs/002-aether-contract-observation/spec.md` §6 permanece intacta: el
manager y el código compartido de observación no importan Hermes; se conservan
las restricciones del adaptador de observación sobre dependencias del manager
y registro de hooks. No existe un límite normativo de tres importadores para
toda funcionalidad futura del paquete.

**Decisión dentro del diseño aprobado:** Supervisor puede reconciliar el
inventario AST con los tres importadores nuevos inspeccionados,
`claude_context.py`, `kanban_worker_launcher.py` y `worker_mcp_server.py`.
Su acceso diferido al contexto Kanban, a la ubicación canónica del board y al
registro de herramientas realiza §3.5, §3.8 y §3.9; no son módulos del manager
ni del flujo compartido de observación. Esta decisión se apoya en esa separación
de responsabilidades y no autoriza dependencias Hermes en los módulos protegidos.
Mantener el escaneo AST, el inventario cerrado por rutas y las otras aserciones
de la misma prueba; no omitirla, aceptar comodines ni reducir gates o cobertura.
Los nombres anteriores identifican el candidato inspeccionado, no revocan §5.
Si la corrección exigiera romper la frontera normativa, devolver la discrepancia
a Morfeo en lugar de ampliar la excepción. Es una reconciliación del oráculo
bajo la integración existente, no otro retorno de C, cambio del contrato ni PASS;
Supervisor conserva la implementación y la evidencia del gate corregido.

## 7. Authority, convergence and stop

Supervisor uses the provisioned profiles and native Project, board and worktrees; it owns
receipt review, decomposition, independent review and routine closeout under R8 FR-824
(branch push, PR, required checks, non-bypass green merge, issue #563 reconciliation and
objective-owned cleanup). Implementer owns local implementation and commits, never
publication. Real Claude Code calls are authorized for the isolated verification run and
bounded focused probes of the exact binary's event sequence, in disposable scope only.

Use the canonical Supervisor convergence procedure: at most two ordinary returns per
logical unit, preserving history across replacement cards. Stop dependent work and return
to Morfeo when:

- `HERMES_BIN` cannot reach the real dispatcher path without a Hermes core change (no
  monkeypatch, second scheduler or drop-in);
- PD-71 cannot be made blocking and fail-closed on Claude with bypass active, or hook
  activation cannot be proven before the work prompt reaches the model;
- the worker MCP server or the hook cannot coexist with the user's own configuration
  without managing that configuration;
- a single writer per worktree cannot be guaranteed;
- MCP readiness cannot be verified deterministically;
- the design would require a Hermes fork change, a new credential, a release or any
  out-of-scope effect; or a genuine protected-edge denial occurs.

## 8. Evidence and closeout

Supervisor authors `tasks.md` and compact per-unit evidence under this objective's
`evidence/` before the implementation PR merges, including the isolated-run record from
[quickstart.md](quickstart.md). After the actual green merge and issue reconciliation,
Supervisor records the final receipt as its terminal closeout attachment and retires
objective-owned worktrees. Morfeo then receives the exact final revision under
`contract-result-review`. Raw logs and disposable roots stay in owned scratch and are
retired after the necessary evidence is preserved.
