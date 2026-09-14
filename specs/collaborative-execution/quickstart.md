# Collaborative execution — runnable verification and acceptance

This is the agreed mechanical/resource verification path, not a campaign proving LLM collaboration quality or non-recurrence. Run tests in isolated task worktrees with disposable state, never on the live objective board. Existing CI remains required; no check/coverage floor is weakened to make this objective green.

## 1. Native mechanics (CE-01..08)

Use the maintained Hermes fork candidate and its normal test interpreter. Add the focused deterministic tests in `tests/hermes_cli/test_kanban_collaboration.py` and `tests/tools/test_kanban_collaboration.py` (or one equivalent focused file if DB/tool ownership is one unit). Extend the existing gateway and TUI test modules for their actual consumer branches. Commands, from the verified fork candidate root:

```bash
python -m pytest -q tests/hermes_cli/test_kanban_collaboration.py tests/tools/test_kanban_collaboration.py
python -m pytest -q tests/tools/test_kanban_tools.py tests/hermes_cli/test_kanban_session_affinity.py
python -m pytest -q tests/gateway/test_kanban_watchers_mixin.py tests/test_tui_gateway_server.py
```

The final receipt records the actual interpreter, checkout revision, selected tests, passes/skips/failures and command. Do not silently run tests against the historical HEAD of the dirty editable install. If an existing native test file was renamed at the selected maintained revision, verify and record its exact replacement before using it. Exclude unrelated expensive model integration suites; transport sinks are controlled functions, not external sends. Test state and counters come from the actual native functions, not fabricated output.

Required positive and negative cases:

1. Opted-in originating root and two child tasks establish one binding; a normal root preserves legacy behavior. Unknown/mixed root, foreign board/Project, forged author/session, absent subscription, closed origin and wrong recipient reject or remain explicitly unavailable without delivery to another session.
2. Request before source completion -> durable pending record -> active recipient enqueue -> explicit acknowledgment -> attributable response -> requester resolution. Verify the source task keeps its claim/status and the independent sibling can still be claimed/run. No completion/unblock is inferred from a reply.
3. Failed queue insertion/steer, process loss after enqueue, resume with an empty in-memory queue, and concurrent consumers preserve/recover one logical pending item without duplicate responses or parent-state mutation. Verify durable delivery/ack/resolution separately.
4. Proactive notice on the specified lifecycle events reaches origin before flow completion without an explicit design-defect signal. Busy-origin events coalesce; explicit requests survive; replies, acknowledgments, heartbeats and ordinary comments do not feed a wake loop.
5. Two origins with identical display names and separate boards/sessions/topics never receive each other's notices. Exact TUI session and gateway source are used. Internal collaboration bypasses passive human pings, while ordinary terminal notifications and real escalation remain unchanged.
6. Peer/worker content is labeled as evidence/advice and is never injected through the genuine user-only out-of-band wrapper. A spoofed body/author, malformed metadata, oversized payload and transport truncation sentinel cannot become owner authority or a partial persisted request.
7. Completed decomposition root does not expire descendant collaboration; terminal flow/archived root does. Controller idle continuation reuses the existing affinity lease/session/workspace, cannot clear blocked dependencies as a side effect, and does not spawn another Supervisor.
8. Revised candidate remains explicit in references; response to an older revision is not auto-applied. Superseded contract/ended flow is marked stale. A stopped/finished task is not restarted to manufacture an answer.
9. Repeated activation/schema initialization is idempotent; pre-existing comments/tasks/subscriptions still read and execute normally. Disable/rollback leaves the history intact and stops new opted-in delivery.

Construct each fixture with scrubbed board/session environment, unique temporary roots and no real gateway dispatcher. Assert the intended temporary board path before creating any card. Do not erase genuine delegated-child identity or use fixture shortcuts that mutate the live board. Controlled native consumer invocations are sufficient; no paid model turn or live Telegram canary is required.

## 2. Aether resources and normal gates (CE-09..10)

From the Aether candidate:

```bash
uv run --frozen pytest -q tests/test_contract_quality_documents.py tests/test_contract_result_review.py tests/test_documentation.py
uv run --frozen pytest -q tests/test_observation_packaging.py tests/test_observation_lifecycle.py
uv run --frozen ruff check src/aether_agents tests
uv run --frozen ruff format --check src/aether_agents tests
uv run --frozen mypy
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/check_hermes_baseline_drift.py --json
git diff --check
```

Use the repo's existing locked environment; do not install tools into another profile. Reconcile literal test/document expectations for the authorized normative delta. Verify that the three SOULs preserve their sectors and role/authority boundaries, the four existing procedures describe request/response/disposition, and documentation no longer implies #317 is an open-ended gate. Preserve immutable historical evidence.

Run required policy CI and package checks normally, including its exact public Hermes baseline and canonical manifest. The new optional fork transport is qualified against the maintained fork separately; do not change the centralized public baseline merely to make the optional tool args appear. Add the new Objective Contract path (and any approved new distributable files/patch paths) to the existing literal canonical base manifest; never replace it with a broad allow glob. Use existing exact-Hermes bootstrap when its tests require it.

Baseline failures, including any surviving coverage floor issue, must be compared at the exact baseline/candidate. Ordinary objective-caused corrections remain in scope. An unrelated defect that genuinely blocks required closeout permits only the smallest reversible unblocker with evidence and issue attribution under project policy; no coverage lowering, skip broadening, check bypass, unrelated refactor or separate release project is authorized. Return a material design defect to Morfeo instead of repeatedly requesting piecemeal fixes.

## 3. Real installation readback (CE-11)

After independent review and normal merge, apply the normal existing adoption workflow:

- Resolve provisioned executable/import paths and affected source bytes, not only Git HEAD.
- Snapshot affected profile/skill files and native sources for rollback; preserve unrelated dirty/installed deltas. Install the reviewed changes through the existing lifecycle/reconciliation procedure, never via a clean-checkout overwrite of the whole live tree.
- Verify exact installed hashes for the three SOULs and modified canonical skills; run the native prompt/skill loader in a disposable profile populated from those installed bytes and verify the full text is loaded under the configured cap, without a model call.
- Inspect actual native tool registration: optional create/comment collaboration arguments and show response are exposed at the installed revision. Run the isolated deterministic smoke using that installed interpreter and temporary state.
- Verify no active worker is interrupted. If plugin/tool loading requires gateway replacement that would kill Supervisor itself, Supervisor safely parks with a durable activation recipe and requests the already-authorized bounded Morfeo cutover through the native origin path; Morfeo performs it from the independent owner session in a verified zero-worker window, then resumes the existing continuation. Do not invent another controller, blanket restart or indefinite watcher.
- State that existing cached conversations may need their normal fresh-session/reload boundary; never rewrite histories or claim those prompts changed merely because files did.

No functional acceptance of the Telegram Monitor, messaging-provider qualification, human screenshot or non-recurrence waiting period is part of this receipt.

## 4. Closeout and evidence (CE-12)

Supervisor records one compact matrix in this objective's `evidence/` directory: criterion, artifact/revision, producer, actual command/result, directly verified versus reused evidence, remaining limit. Morfeo's final reception reuses applicable evidence and checks decisive doubts, not a mandatory full rerun. Root completion releases decomposition; terminal pipeline completion requires implementation review, integration, prescribed checks and scoped adoption.

Close #334 as the delivered scoped collaboration mitigation and #317 as owner-directed retirement of open-ended observation without an organic PASS. Add a final linked note to already-closed #407, preserving stopped-objective history. Record both repository PRs/merge revisions, normal green checks, exact runtime adoption, rollback and owned-residue cleanup. Do not report 'never happens again' or a made-up improvement percentage. Preserve active/unmerged/unrelated branches, worktrees, stashes, boards and sessions. Classify `release_impact` from compatibility evidence; `release_action=defer`, `release_channel=none`.
