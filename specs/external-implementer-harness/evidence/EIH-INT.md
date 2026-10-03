# EIH-INT evidence — integration, isolated real run and closeout

**Unit:** EIH-INT (terminal integration card `t_45ed8737`)
**Objective Contract:** `oc_f1ea2c4a2e0662da@v1`
**Owning issue:** [#563](https://github.com/DarkArty07/Aether-Agents/issues/563)
**Integration branch:** `aether-agents-2/t_d066909f-execute-oc_f1ea2c4a2e0662da-v1-opt-in-cl`
**Producers:** Supervisor (runs 23–25, through the `needs_input` stop). After that stop,
the owner-directed completion (spec OD-11) was carried out in a Claude Code session on
2026-10-03 and is attributed separately below.

## 1. Integration

Every independently reviewed unit was merged by ordinary merge, preserving each unit
commit. No squash, amend, rebase or other history rewrite was used.

| Input | Commits |
| --- | --- |
| Design (Morfeo) | `2221302f`, `d7493cf8`, `a10c270a`, `7a6a0b6a`, `e72c657c`, `d37f87db` |
| EIH-A selection and projection | `fd1e7128` |
| EIH-B launcher and `HERMES_BIN` override | `af9ab4ad` |
| EIH-C adapter, readiness, worker MCP, PD-71 hook | `8adac14d` → `6306ffb0` → `a8f9aab0` |
| EIH-D guidance and documentation | `4796c290` |

Integration corrections, each in its own commit:

- Supervisor: `384c7ada` routes a missing current-run claim to Hermes (see EIH-B §5).
  `fe770802` and `31b42e78` accept the reviewed `aether-kanban-worker` console script
  in the lifecycle identity checks, including the historical rc16 qualification.
  `aef40b81` lists the new tracked files in the canonical base manifest. `0fb87bdc`
  reconciles the import-boundary oracle with the design clarification `d37f87db`.
- Owner-directed completion: `063fdafe` ends the single Claude turn and reads the
  documented failure fields (EIH-C §9; plan §3.11; research §3.2).

Supervisor's integrated gate at `31b42e78` passed on 2026-10-03: `run_tests.py` 1763
passed, 64 skipped, and every other quickstart §2 check passed. The log is attached to
card `t_45ed8737`, SHA-256 `9a61b853ac343effd0d9fe9e0705a4d75081ad29c81b672add30ea8f0aa75e35`.
The gate result for the final revision is in §4.

## 2. First isolated run (run 26) and its disposition

This was the one real run the contract originally allowed. Supervisor used the
disposable board `eih-realrun`, card `t_2bbfc2f4`, Claude Code 2.1.288 and native
`dispatch_once`, with `HERMES_BIN` set to the candidate launcher.

- The pre-prompt gate opened at 02:39:00–02:39:03Z with correlated bypass `initialize`,
  a connected derived worker surface and a matching nonce, and the work prompt was
  delivered.
- At 02:39:04Z the first model call returned `model_not_found`/404. The owner's
  then-default Claude model was an alias reachable only through a local router, and the
  attempt environment did not carry that router. That absence is consistent with OD-4.
- There were no tool calls, commit, comment, receipt or transition. The CLI stayed
  alive without activity for more than two hours. The reconciliation is attached to the
  card, SHA-256 `904e4fa65ab195b7e28d8bedfd8f8bc757d67eb5676840de5c306e8c5dfb683e`.

Disposition (2026-10-03, OD-11): the hang came from adapter defects, which `063fdafe`
corrects. The owner authorized a replacement run. A one-line headless probe of the
owner's Claude configuration then resolved a subscription model. Aether neither read
nor changed that configuration; it observed only the probe's result. The retained
run-26 sandbox was retired after this record.

## 3. Replacement isolated real run (EIH-12, quickstart §3)

**Setup** (owned disposable scope, removed afterwards):

- The Hermes/Kanban root held a minimal `implementer` profile, made from the
  candidate's SOUL with model provider `none` and no credentials.
- The disposable Git repository had one commit, `9a7bbf76`.
- Board `eih563-realrun` was written by the candidate's own handoff writer
  (`_create_metadata_exclusive`) with the Aether contract identity and
  `aether_implementer_harness: "claude-code"`. Only the unregistered runtime project
  scope was cleared, through the native `write_board_metadata(project_id="")`.
- Card `t_96bd522a`, assigned to `implementer`, asked for this: write `hello.txt`
  containing `hello from claude`, commit it, and request review.
- One native `dispatch_once` tick ran on the rc17 Hermes source. `HERMES_BIN` pointed
  to the candidate `aether-kanban-worker`, which runs candidate `src` on the rc17
  runtime interpreter (Python 3.13.15). Every inherited `HERMES_KANBAN_*` variable was
  unset.
- The dispatch ran under a clean environment (`env -i` with `HOME`, `USER`, `PATH`,
  `LANG`, `XDG_RUNTIME_DIR`), so this session's Claude Code variables did not leak in.
  The owner's live Hermes homes, boards and runtime selector were not used.

**Result** (2026-10-03, Claude Code 2.1.288, session `299edb16-6a77-45c2-be3a-4c4852be739b`):

| Observation | Value |
| --- | --- |
| Dispatch → claim/spawn | 08:02:46Z; run 1 claimed and the candidate launcher spawned |
| Transition by this run | `review_requested` (run outcome `review_requested`, task `review`) |
| Commit in the disposable repository | `c0320bb` "hello from claude"; `hello.txt` is exactly `hello from claude\n` |
| Executor comment | `aether-executor: claude-code 2.1.288 session=299edb16-6a77-45c2-be3a-4c4852be739b outcome=review_requested` |
| Receipt | `aether.harness-receipt.v1`, outcome `review_requested`, `fallback=false`, `exit_status=0`, 08:02:47Z–08:03:32Z |
| Pre-prompt readiness | correlated `initialize` success with `current_permission_mode: "bypassPermissions"`; correlated `mcp_status` with `aether-worker` `connected` and every required tool; matching `SessionStart` nonce |
| PD-71 hook log | 9 evaluations: `ToolSearch`, `mcp__aether-worker__kanban_show` → `kanban_show`, `Bash` → `terminal` ×3, `Write` → `write_file` ×2, `mcp__aether-worker__kanban_request_review` ×2; all in `bypassPermissions`, all allowed |
| Hermes pass-through | none: the adapter returned 0, no `execv` happened, and the sandbox Hermes `state.db` has zero sessions |
| Transient inputs | the attempt directory was removed when the attempt ended |

**Observed coexistence (OD-4):** the owner's own Claude configuration was loaded
unchanged. Its own `PreToolUse` fact-forcing hook denied the first `Bash` and the first
`Write` until Claude stated the requested facts. Both that hook and Aether's PD-71 hook
ran on every call. The first `kanban_request_review` omitted a reviewer; the native
board refused it ("an initial review requires an explicit independent reviewer"), and
Claude retried with `reviewer="supervisor"`.

**Limits:**
- The disposable profile does not load the Aether plugin, so the derived worker surface
  held the 12 Kanban worker tools without `project_knowledge` and `work_memory`. Their
  exposure stays covered by the focused worker-MCP tests (EIH-C §3).
- The gateway plugin's in-process override is covered by focused tests, not by this
  run.
- This run proves one working path. It is not installed availability, a Supervisor
  review on the installed runtime, agent-behavior qualification or a PD-74 result.

## 5. Criterion mapping

| Criterion | Evidence |
| --- | --- |
| EIH-01 / AC1 | EIH-A byte-identity tests; EIH-B exact pass-through tests including board/database read failures |
| EIH-02 / AC2 | EIH-A selection, supersede, rejection, projection, reuse-conflict and rc17-reader tests |
| EIH-03 / AC3 | EIH-B plugin-override and per-condition routing tests (43 launcher tests with `384c7ada`) |
| EIH-04, EIH-05 / AC4 | EIH-C command, forbidden-flag, context and skills-plugin tests; §3 run |
| EIH-06 / AC5 | EIH-C worker-MCP tests; §3 run (connected derived surface, identity-bound calls) |
| EIH-07 / AC6 | EIH-C PD-71 adapter tests; §3 hook log |
| EIH-08, EIH-10 / AC7 | EIH-C readiness and fallback tests; `063fdafe` turn-end and signal regressions; §3 readiness observation |
| EIH-09 / AC8 | Receipt, comment and zero-session observations in §3; focused receipt tests |
| EIH-11 / AC9 | EIH-D guidance and documentation; documentation and public-artifact checks (§4) |
| EIH-12 / AC10 | §3 |
| AC11 | §4 gate, then the normal PR, required checks, merge and #563 reconciliation recorded on the issue |

## 6. Compatibility and release

Aggregate compatibility of this objective is `minor`: additive and opt-in, with the
default Hermes path and earlier readers unchanged. Under OD-11 the release is prepared
separately as RC18. That release also carries earlier unreleased `main` changes, and
its own record owns the release conclusions.

## 7. Cleanup

After §3 was recorded, the disposable scopes of both isolated runs were removed. That
covers each run's Hermes root, board, repository, launcher wrapper and attempt
temporary directory, plus the run-26 scratch evidence files already attached to the
card. The receipts for the two disposable boards under the Aether state root were also
removed after they were recorded here. Objective-owned unit branches and worktrees are
retired after the merge.
