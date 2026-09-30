# Implementation Evidence — Unit EIH-C: Claude Code Adapter, Readiness, Worker MCP and PD-71 Hook

**Status:** Implementation complete and verified with focused unit test suites. Ready for same-card Supervisor review.

**Unit ID:** `EIH-C`
**Task ID:** `t_be9fc19e`
**Objective Contract:** `oc_f1ea2c4a2e0662da@v1` ([#563](https://github.com/DarkArty07/Aether-Agents/issues/563))
**Decomposition Breakdown:** `specs/external-implementer-harness/tasks.md` (commit `ab99a2f8`)
**Base Commit:** `2221302f1c93fb4ffd166df9b5482aa2fecaef7a`
**Installed Claude Code Version:** `2.1.285`

---

## 1. Scope and File Boundaries

### Created Files
- `src/aether_agents/claude_code_adapter.py`: Main adapter implementing `run_attempt(argv, env)` per Shared Decision 14a, invocation, readiness gate, process group lifecycle, signal forwarding, heartbeat, outcome classification, receipts, and stateless Hermes fallback via `os.execv`.
- `src/aether_agents/claude_adapter.py`: Canonical alias module re-exporting `run_attempt`.
- `src/aether_agents/claude_context.py`: Appended system prompt context builder, tool equivalence table, task-pinned skills loader, Implementer canonical skills plugin builder, and initial user prompt builder.
- `src/aether_agents/worker_mcp_server.py`: FastMCP stdio server named `aether-worker`, deriving the Kanban worker tool surface and binding to the attempt identity.
- `src/aether_agents/pd71_claude_hook.py`: Fail-closed PreToolUse command hook adapter mapping Claude tool payloads onto the unchanged `aether_pre_tool_policy.py`.
- `tests/test_claude_code_adapter.py`: Focused lifecycle, readiness, classification, and fallback tests with stub Claude.
- `tests/test_worker_mcp_server.py`: Focused worker MCP surface, argument forwarding, and identity enforcement tests.
- `tests/test_pd71_claude_hook.py`: Focused PD-71 translation, blocking, and fail-closed evaluation tests.

### Preserved Files (Strictly Untouched)
- `policy/hooks/aether_pre_tool_policy.py`: Preserved unchanged byte-for-byte.
- `src/aether_agents/objective_contracts/store.py`: Preserved untouched (owned by EIH-A).
- `src/aether_agents/objective_contracts/hermes_plugin.py`: Preserved untouched (owned by EIH-A and EIH-B).
- `pyproject.toml`: Preserved untouched (owned by EIH-B).
- `src/aether_agents/lifecycle.py`: Preserved untouched.
- `src/aether_agents/resources/*`: Preserved untouched.
- `KANBAN_GUIDANCE`: Imported at run time from `agent.prompt_builder`; never copied into Aether source.

---

## 2. Adapter Seam (Shared Decision 14a)

EIH-C implements exactly:
```python
def run_attempt(argv: list[str], env: dict[str, str]) -> int:
    ...
```
- `argv`: The full argument vector built by the dispatcher (`argv[0]` included).
- `env`: The dispatcher-built environment mapping.
- Returns `int`:
  - `0` after a native Kanban transition (`review_requested`, `completed`, `blocked`) by this run.
  - `76` for a clean exit (code 0) without a transition.
  - `143` after a propagated SIGTERM.
- Does not return on fallback: Replaces current process via `os.execv` with the Hermes pass-through resolved from `PATH` or `[sys.executable, "-m", "hermes_cli.main"]` using the original `argv` tail and `env`, without reading `HERMES_BIN`.

---

## 3. Worker MCP Surface (AC5 / EIH-06)

The `aether-worker` stdio MCP server derives its surface dynamically at startup from the Hermes tool registry for the `implementer` profile. The exact exposed tool list contains 14 tools:

1. `kanban_attach`
2. `kanban_attach_url`
3. `kanban_attachments`
4. `kanban_block`
5. `kanban_comment`
6. `kanban_complete`
7. `kanban_create`
8. `kanban_heartbeat`
9. `kanban_link`
10. `kanban_request_changes`
11. `kanban_request_review`
12. `kanban_show`
13. `project_knowledge`
14. `work_memory`

Excluded tools per plan §3.9: file (`read_file`, `write_file`, `patch`), terminal (`terminal`, `execute_code`, `read_terminal`, `read_preview`, `read_window_below`), search (`search_files`), web (`web_search`, `web_extract`), memory (`memory`), session (`session_search`), skills (`skills_list`, `skill_view`, `skill_manage`), delegation (`delegate_task`), todo (`todo`), interactive (`clarify`, `process`, `vision_analyze`), and Morfeo tools (`objective_contract`, `morfeo_bootstrap`).

Calls delegate directly to native handlers via `tools.registry.registry.dispatch`, enforcing:
- Task/run/claim ownership checks via `tools.kanban_tools._enforce_worker_task_ownership` (mutations on foreign task IDs are rejected).
- Forwarding only supplied arguments (dropping `None` optional values per #556 bridge behavior).

---

## 4. Readiness Gating via Native Stream-JSON Control Protocol (Plan §3.7)

Initial assumption and investigation history:
- An earlier probe checked `system/init` for MCP status. During same-card review of candidate `8adac14d`, Supervisor's probe of Claude Code `2.1.285` found that `system/init` listed all MCP servers as `pending` or `needs-auth` with no `mcp__` tools.
- Morfeo resolved the observational premise in collaboration response 7 (commit `a10c270a`, plan §3.7, research §3.1) by establishing that the deterministic pre-prompt observable on Claude Code `2.1.285` is the native stream-json **control protocol**, not passive `system/init` inspection.
- The readiness gate in `claude_code_adapter.py` enforces positive evidence of all three invariants before any work prompt reaches Claude's stdin:
  1. **Correlated `initialize` control response:** Executor emits `control_request` `initialize` with a unique `request_id` and `hooks: null`. A matching `control_response` must return `subtype: "success"` and `current_permission_mode: "bypassPermissions"`.
  2. **Correlated `mcp_status` control response:** Executor emits `control_request` `mcp_status` with a unique `request_id`. A matching `control_response` must return `subtype: "success"`, explicit `status: "connected"` (never absent, pending, or ready), and `tools[].name` containing every tool in the derived required worker surface for this attempt (14 tools). If previously reported `pending`, it is polled until connected or timeout.
  3. **`SessionStart` nonce:** A matching nonce file written by the per-attempt `SessionStart` command hook from the same settings that register the blocking PD-71 `PreToolUse` hook.
  4. **Privacy preservation (commit `7a6a0b6a`):** Raw control replies (which may contain headers, env, or configuration of other MCP servers) are filtered out and never persisted into receipts or the failure stream tail.
  5. **Later `system/init`:** Treated as corroborating run evidence, never a substitute for the pre-prompt control handshake.
  6. **Prompt Submission:** Only after all three invariants are proven is the initial work prompt (`"Work Aether Kanban task <id>.\n\n" + worker_context`) written to stdin.
- **Live observation status:** Real observation against a live Claude Code process with the full production worker MCP server is not yet done; it is scheduled for the one isolated real run in terminal integration unit `EIH-12` per plan §6 / quickstart §3.

---

## 5. PD-71 Hook Adapter (AC6 / EIH-07)

The `pd71_claude_hook` module runs as a `PreToolUse` command hook with matcher `*`:
- Translates Claude tool payloads:
  - `Bash` -> `terminal` (`command`)
  - `Write` -> `write_file` (`path`, `content`)
  - `Edit` / `MultiEdit` / `NotebookEdit` -> `patch` (`path`, edit text)
  - `mcp__aether-worker__<tool>` -> `<tool>` with original arguments
  - Other tools keep their names and inputs
- Pipes translated JSON to the unchanged `aether_pre_tool_policy.py` in an isolated implementer profile location (`ROLE = implementer`).
- Exits 0 on allow; exits 2 with policy reason on stderr on policy block.
- Fails closed: unparsable input, missing policy, adapter error, or internal timeout (>5.0s) immediately exits 2.
- Logs `permission_mode` and decision to `hook.log` in the attempt directory.

---

## 6. Process Lifecycle, Fallback, and Receipts (AC7, AC8 / EIH-08, EIH-09, EIH-10)

- **Process Group Isolation:** Claude runs in a new session group (`os.setsid`) with Linux parent-death signal (`PR_SET_PDEATHSIG` -> `SIGTERM`). SIGTERM/SIGINT on launcher are forwarded to the group (`os.killpg`).
- **Post-exit Termination:** When Claude exits, remaining group members are terminated (`SIGTERM`, grace period, `SIGKILL`), waiting until `os.killpg(child_pid, 0)` raises `ProcessLookupError`.
- **Single-Writer Verification:** Prior to any fallback, `/proc/*/cwd` is inspected. If any process other than the launcher has its working directory inside `HERMES_KANBAN_WORKSPACE`, fallback is refused and the launcher exits 1.
- **Heartbeat:** `heartbeat_current_worker_from_env()` is called on real stream events, rate-limited to at most once per 30 seconds.
- **Outcome Classification:**
  - Native transition on board (`review_requested`, `completed`, `blocked`) -> exit 0.
  - SIGTERM received -> exit 143.
  - Task cancelled or claim lost -> exit without fallback.
  - Clean success (exit 0) without transition -> exit 76 (kernel protocol code).
  - Readiness failure, structured auth/billing/rate-limit error (`system/api_retry`), crash, or non-zero exit -> fallback.
- **Receipts:** Written to `<XDG_STATE_HOME>/aether/external_harness/<board>/<task>/run_<run>/receipt.json` with schema `aether.harness-receipt.v1`. On failure or fallback, bounded stream tail (`<= 256 KiB`) is preserved in `stream_tail.log`.
- **Kanban Comment:** Posted using native kanban tool: `aether-executor: claude-code <version> session=<id> outcome=<outcome>` (plus `cause=<cause>` on fallback).
- **Cleanup:** Transient attempt directory (context file, MCP config with claim lock, settings with nonce command, plugin directory) is completely removed at attempt close.

---

## 7. Verification Results

All 43 focused unit tests pass:

```bash
uv run --frozen pytest -v tests/test_claude_code_adapter.py tests/test_worker_mcp_server.py tests/test_pd71_claude_hook.py
```
Output: `43 passed in 17.51s`.

Static analysis and checks:
- `uv run --frozen ruff check src/aether_agents/ tests/`: `All checks passed!`
- `uv run --frozen ruff format --check src/aether_agents/ tests/`: `150 files already formatted`
- `uv run --frozen mypy src/aether_agents`: `Success: no issues found in 59 source files`
- `uv run --frozen python scripts/check_documentation.py`: `documentation validation passed`
- `uv run --frozen python scripts/check_public_artifacts.py`: `public artifact path scan passed: tracked surface + 0 artifact(s)`
- `git diff --check`: `PASS` (clean diff, no whitespace or boundary issues)

---

## 8. Compatibility Conclusion

Unit compatibility impact: `minor` (additive, opt-in Claude Code harness adapter; default path and earlier readers preserved unchanged).
