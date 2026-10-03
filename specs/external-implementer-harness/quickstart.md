# Validation quickstart: external Implementer harness

Runnable checks for [plan.md](plan.md) §6. Commands follow `CONTRIBUTING.md`; test file
names are chosen by the implementation and recorded in evidence. Nothing here authorizes
a release, managed update, installed activation or use of live boards.

## 1. Focused checks while iterating

Run the narrow tests for the unit being changed, for example
`uv run --frozen pytest <new or affected test files> -q`, covering at least:

- **Contract selection:** `begin`/`supersede` semantics; `hermes` and omission render the
  pre-change bytes; `claude-code` renders the key; unknown values and use on other actions
  are rejected; an rc17-style parser accepts a selected final contract.
- **Board projection:** creation with and without selection; reuse equality, including
  absent/absent; mismatch raises the identity conflict.
- **Plugin override:** `HERMES_BIN` set only for a valid release launcher resolved outside
  `runtime/current`; unchanged otherwise; idempotent.
- **Launcher routing:** with a stub `hermes` that records argv/environment, each §3.5
  condition independently forces an exact pass-through; decision exceptions pass
  through; a fully eligible attempt reaches the adapter.
- **Adapter and fallback:** with a stub `claude` emitting canned stream-json — the
  matched control responses in plan §3.7 open the gate only with effective bypass,
  a connected worker and every required tool, plus the matching nonce; absent status,
  missing tools or a foreign request ID never release the work prompt. Readiness
  failures (MCP missing, bypass off, nonce missing, timeout), auth/billing/rate-limit
  signals, crash and error results each fall back exactly once by `execv`; clean exit
  without a transition exits 76; SIGTERM, cancellation, lost claim and a surviving writer
  never fall back; the process group is empty before fallback; the command never contains
  a forbidden flag.
- **Context and skills:** SOUL, `implementation-evidence`, runtime `KANBAN_GUIDANCE`,
  pinned skills and the equivalence table are present; the plugin holds exactly the
  Implementer role skills; no write reaches the project or personal skill directories;
  transient inputs are removed at the end.
- **Worker MCP:** exposed tools equal the derived worker set; calls are identity-bound;
  only supplied arguments are forwarded; no Morfeo or unrelated tools.
- **PD-71 adapter:** Claude-shaped `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` and
  `mcp__aether-worker__kanban_create` payloads reach the unchanged policy with the right
  mapping; a policy block exits 2; malformed input, missing policy and internal timeout
  exit 2.
- **Receipts:** receipt fields and the `aether-executor:` comment line; no Hermes session
  row is created.
- **Guidance:** Morfeo SOUL and `objective-contract-design` carry OD-1.

## 2. Integrated repository gate

Before handoff, on the candidate revision:

```bash
uv run --frozen python scripts/run_tests.py
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
uv run --frozen mypy src/aether_agents
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/check_public_artifacts.py
uv build
git diff --check
```

Confirm the built wheel declares the `aether-kanban-worker` console script and contains
the new modules. Required PR checks remain an independent gate; do not remove, skip or
weaken tests or thresholds to get green.

## 3. One isolated real run (EIH-12)

Purpose: prove once that a real Claude Code attempt, dispatched by the native dispatcher
through the candidate launcher, completes a disposable Implementer card and delivers it
to review through the real Kanban tools. Real Claude calls use the owner's already
provisioned Claude Code login; no Hermes model credentials are needed or copied.

1. **Disposable roots.** Check free space, then create one owned disposable directory
   holding: a Hermes/Kanban root with a minimal `implementer` profile from the candidate's
   profile resources (no credentials); a disposable Git repository with one commit; and an
   execution board whose metadata carries an Aether contract identity and
   `aether_implementer_harness: "claude-code"`. Unset any inherited `HERMES_KANBAN_DB`.
   Never touch the owner's live Hermes homes, boards, sessions or runtime selector.
2. **One card.** Create an Implementer task with a trivial body, for example: create
   `hello.txt` containing `hello from claude`, commit it on the task branch and request
   review with a one-line summary.
3. **Dispatch natively.** Run one tick of the native `dispatch_once` from the candidate
   code with `HERMES_BIN` set to the candidate `aether-kanban-worker`, the same resolution
   the plugin performs. Do not build the spawn by hand.
4. **Observe and record** after the attempt ends: task status `review` with the transition
   made by this run; the commit in the disposable repository; the `aether-executor:`
   comment and the receipt (Claude version, session id, outcome); pre-prompt matched
   `initialize` response (`current_permission_mode: "bypassPermissions"`) and
   `mcp_status` response (`aether-worker.status: "connected"`, every required tool)
   per plan §3.7; the matching `SessionStart` nonce; any later `system/init` as
   corroboration rather than the readiness oracle; hook-log entries showing PD-71
   evaluated the Claude tool calls; and that no Hermes pass-through occurred.
5. **Clean up.** Preserve the record in this objective's `evidence/`, then remove the
   disposable roots. Report any retained path with its reason.

Limits: the run exercises the dispatcher, launcher, adapter, MCP server, hook and receipt,
but not the gateway plugin's in-process override (covered by focused tests) nor a live
Supervisor review on the installed runtime (future owner-authorized release). Fallback is
covered deterministically in §1, not by a second real run.

## 4. Decisive result

Acceptance needs EIH-01–EIH-12 mapped in `evidence/` with revision, command, producer,
result and limits; the isolated-run record; required PR checks green; normal merge and
issue #563 reconciliation. Focused tests prove deterministic source behavior and the
isolated run proves the path once. Neither is installed availability, a qualified agent
behavior or a PD-74 reliability result.
