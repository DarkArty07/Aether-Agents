# CE-INT — integration, dual-repo closeout, adoption

**Status:** integration and publication in progress. This is Supervisor terminal evidence, not owner-objective acceptance.

- **Task ID:** `t_c815d3a4`
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`)
- **Aether integration branch:** `aether-agents-2/t_5fe2c707-execute-active-morfeo-collaboration-cont`
- **Maintained-fork merge:** `DarkArty07/aether-hermes` PR #11, `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`
- **Fork Actions:** disabled (`enabled=false`) — NOT RUN, not green

## 1. Independently reviewed units consumed

Every implementation unit below was independently reviewed on the same-card Supervisor lane before integration. History is merge-commit only; no squash, amend, or rebase.

| Unit | Card | Review | Aether tip | Fork candidate |
| --- | --- | --- | --- | --- |
| Root decomposition | `t_5fe2c707` | n/a (handoff) | `8f452ee7dfbb64cfbc97aeca96ab49e4333b078d` | — |
| CE-AE-RES | `t_08cec910` | round 2 approved | `08ae064e5051a27afac32982bd9bff7bb21c4da2` | — |
| CE-AE-DOCS | `t_e890e56a` | round 2 approved | `9f4ba65ea48163934ff14ee034655d23591330c2` | — |
| CE-HF-CORE | `t_07e9bbd7` | round 2 approved | `763d221134980576eb847a41e55643a56a59f1d3` | `20db06c0b8441190830aa72e3c0de6fdce6b8db4` |
| Morfeo D5 origin-route | design commits | Morfeo-owned | `dd2f1aa449b2e9fc7ab808089a98e35146b51fb8` | — |
| CE-HF-DELIVER | `t_8edf43f3` | round 4 approved | `7b6e28a1f4ff6b77cd8c2b464555a760b369dd42` | `2ec004ea54ab2401f63f1885a7c26f59bf1eb7db` |

Fork ancestors of `origin/aether-main` after PR #11: CORE `20db06c0` and DELIVER `2ec004ea` are both ancestors of `bb5e9a422f`.

## 2. Criterion matrix

| Criterion | Artifact / revision | Producer | Command / result | Direct vs reused | Limit |
| --- | --- | --- | --- | --- | --- |
| CE-01 opt-in binding | fork `2ec004ea54` / merge `bb5e9a422f` | CE-HF-CORE + D5 | Collaboration suites 53 passed in 8.07s on candidate interpreter | reused unit review; INT re-ran 53 | Extra notify subscribers are not recipients; missing `origin_route` stays unavailable |
| CE-02 request before completion | same | CE-HF-CORE | `test_request_respond_ack_resolve_lifecycle` in the 53 | reused + INT re-run | No live Telegram/model |
| CE-03 proactive notices | same | CORE enqueue + DELIVER origin reach | lifecycle/coalesce tests in the 53 | reused + INT re-run | Controlled sinks only |
| CE-04 persist/enqueue/ack/respond/resolve | same | CE-HF-CORE | claim/lease/dedup tests in the 53 | reused + INT re-run | Synthetic live-board residue preserved, not deleted |
| CE-05 peer evidence / truncation | same | CE-HF-CORE | truncation/malformed/author-not-forged/peer-label tests in the 53 | reused + INT re-run | Not owner-instruction injection |
| CE-06 TUI/gateway exact origin | same | CE-HF-DELIVER | exclusivity both tick orders; no passive ping; notify cursor intact | reused + INT re-run (671 neighbors) | Fake sinks labeled as such |
| CE-07 controller lease / no duplicate Supervisor | same | CORE + DELIVER | advisory worker_context and flow_attention pins | reused unit review | No parent unblock from advisory |
| CE-08 stale / root-done not terminal | same | CE-HF-CORE | archive/flow_terminal vs root-done tests | reused + INT re-run | `resolution=stale` on archive |
| CE-09 roles/skills/docs | Aether `08ae064` + `9f4ba65` | CE-AE-RES + CE-AE-DOCS | resource/docs gates re-run at INT | INT re-run | Resource tests are not behavioral qualification |
| CE-10 fork + Aether distribution | PR #11 `bb5e9a422f`; portable patch SHA-256 `94b95f2153bce69947a9f7369cebe559b56826c49fa22f4aa1eb2b587acdef30` | CE-INT | reconstruction 8/8 byte-equal; `git apply --check` exit 0 | direct | Fork Actions NOT RUN |
| CE-11 runtime adoption | live editable `0b288979e2` (dirty) | CE-INT | pending: reconstruct+canary; gateway is this worker's parent so no self-restart | pending | See section 5 |
| CE-12 GitHub/issue/residue | this card | CE-INT | fork PR merged; Aether PR pending this commit | in progress | Unverified long-term efficacy retained |

## 3. Integrated fork verification (direct)

Interpreter: nested candidate `.venv/bin/python` resolving `hermes_cli.kanban_db`, `tools.kanban_tools`, `gateway.kanban_watchers`, `tui_gateway.server` to the DELIVER tree at `2ec004ea54`. `HERMES_TEST_FILE_RETRIES=0`. Live `HERMES_KANBAN_DB`/`BOARD`/`TASK` unset.

- Collect-only collaboration: 53 tests
- Collaboration run: 53 passed in 8.07s
- Neighboring regression: 671 passed in 39.66s
- `git diff --check 3b81e9d91cc3a0662b910726a44c94ed328b1e90...HEAD`: exit 0

## 4. Live-board residue (preserve)

Direct SQL deletion is never cleanup. Observed on the objective board at INT start: 18 tasks (6 objective + 12 synthetic) and 3 `kanban_collaboration` rows. Synthetic ids: `t_b421fb57`, `t_9acc568c`, `t_01a3ab74`, `t_2406142e`, `t_0048472c`, `t_20202d6f`, `t_f3e60446`, `t_709f9ebd`, `t_6c84236c`, `t_1e75d385`, `t_ebd28f85`, `t_c46db090`. Related: Aether #267 reopened from the DELIVER probe; #417 observer timeout and #421 TUI SIGBUS remain out of scope.

## 5. Runtime adoption limit

This Supervisor worker is a child of morfeo gateway PID 893. Self-restart would kill this closeout. Adoption of live editable bytes is therefore a post-merge or Morfeo-cutover step: reconstruct `live = snapshot + HLP-334 patch` without resetting unrelated dirty files, then restart in a verified zero-worker window. Until that cutover, installed-byte/schema readback of the live runtime is not claimed.

## 6. Release conclusions (aggregate)

- `release_impact = minor` — compatible optional public additions (create/comment collaboration object, adjunct table, show collaboration list). No incompatible removal.
- `release_action = defer` — merge does not imply a release; no tag, package, or GitHub Release.
- `release_channel = none`

## 7. Out of scope (explicit)

Telegram Monitor restart; Aether #417 observer repair; Aether #421 TUI SIGBUS repair; organic PASS / measured speedup / non-recurrence; force-push; check bypass; package publication.
