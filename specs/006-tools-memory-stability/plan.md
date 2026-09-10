# Technical plan — tools, memory and runtime stability

## Inspected bases and selected boundaries

Aether main: cc93451799ded171c38fea98188e02fd75b0fe74. Diagnostic behavior was exercised
at b1baad948bc21e956d291c8d40abb2add6033b3c; the intervening commit changes Supervisor
review convergence/guidance, not the diagnosed binding/privacy/reducer code.
Maintained runtime source: DarkArty07/aether-hermes,
aether-main@266e412fb83ad32af92ed391db942f88993d76a2.
Upstream comparison for the guard: NousResearch/hermes-agent@
2ddeba9e17a1df5471802481e3efef20885a20b2.
Public qualification baseline remains e624e9fde561e1add9388384012b295fde669ade.
Refresh exact source and compare relevant files before repair; do not merge an entire
upstream or dirty live tree. Runtime paths/selection and role models are private
execution side data, not committed design.

## TS-373: binding resolution

Owning components: src/aether_agents/knowledge/bindings.py (_native_workspace,
context_for_session), knowledge/context.py (resolve_context), native knowledge plugin.
Current order raises for an ordinary non-Git native cwd before explicit binding lookup.

Selected behavior: classify native evidence before deciding precedence. Absent/empty
metadata and an ordinary existing directory proven to have no Git repository context
may fall through to the explicit binding for the exact native role/session. A usable
native project and explicit binding must agree. Missing/unreadable paths, malformed
Git metadata, Git failure in an apparent repository, copied markers, unknown UUIDs,
unregistered worktrees and contradictory native evidence remain errors; do not catch
all KnowledgeError exceptions and silently fall back. Resolve ancestors through the
existing Git operation rather than treating a subdirectory as a new project.

Preserve public tools and error envelopes, role/session identity source, common-directory
and marker checks. Do not accept project/path/role overrides from tool arguments, select
by display name/recency, rewrite SessionDB, or auto-create a binding. Internal classifier
names and equivalent implementation are local choices.

Tests extend tests/test_knowledge_plugin_cli.py and the native PluginContext boundary.
Positive cases: null, empty, ordinary non-Git cwd with valid explicit binding; native
project cwd and subdirectory; attached worktree. Negative cases: no explicit binding,
another session/role/project, malformed Git marker, copied/unregistered checkout,
unreadable native evidence. Check graph resolution and actual work-memory save/read in
an isolated project/component fixture, followed by the scoped native operator canary.

## TS-390: typed finish-reason counts

Owning components: observation/capture/projectors.py, reduce/reducer.py
(model_context_economics), privacy.py, storage.py (ReadModel.record_summary), query.py.
The current summary schema already defines finish_reasons as an opaque-key object of
non-negative integers. Preserve that public shape and exact count/key meaning.

Selected design: recognize the schema-owned histogram only at
$.model_context_economics.finish_reasons, with bounded safe names and strict integer
counts. Preserve privacy checks on names and reject raw content, nested data,
booleans/floats where integers are required, negative counts and invalid names. The
words tool_calls and error in this typed data namespace are not raw payload fields.
All other locations retain the existing forbidden-key behavior. Do not delete global
forbidden keys, broadly allow dictionaries, rename counts, drop failing events, disable
validation or change a real failure into empty output. Prefer a narrowly shared typed
validator over duplicated schema interpretation if the existing contracts module permits.
No schema-version or storage migration is expected for the selected compatible fix.

Tests must traverse EventBuilder.model_request -> event persistence -> reduce_events ->
ReadModel.record_summary -> compact query/report. Existing EventFactory.summary validates
JSON schema only, which is why current reducer tests miss the privacy/storage boundary.
Cover stop/tool_calls/error plus the raw-payload negative matrix and existing deterministic
reduction/coverage/isolation tests. Real observation must read an affected contract after
candidate adoption; do not rewrite its authoritative events or bypass privacy to pass.

## TS-389: command syntax versus referenced data

Runtime owners: cron/lifecycle_guard.py and tools/shell_heredoc.py; terminal entry is
 tools/terminal_tool.py. Current segment splitting treats a Python Path(...) argument
inside a heredoc as a standalone executable and scans the referenced log as shell.

Selected design: give the referenced-script walker a syntax-aware view in which a
well-formed, terminated, quoted Python stdin heredoc body cannot create shell executable
references. Retain the original source for direct lifecycle detection and appropriate
real shell/script traversal. Reuse the existing parser where it preserves these two
separate views. Do not exempt Python wholesale, hide all heredoc bodies from every
check, whitelist file extensions, or make an arbitrary data filename an executable.
Malformed/unterminated/ambiguous heredocs retain conservative behavior. Reconcile
affects of shell expansion/substitution rather than claiming quoted data executes.

Required controls: harmless Python heredoc reading a log with lifecycle-looking data;
equivalent Python -c; harmless shell data heredoc; real direct lifecycle commands;
referenced real shell script; Python source with a real lifecycle subprocess call;
malformed/unquoted shell-capable forms. Invoke analysis functions or a supervised
terminal test double for dangerous controls, never execute real restart/stop commands.
Run terminal/guard regression suites. Current upstream reproduces the false positive
and loses a control detected by the maintained source, so blind cherry-pick is rejected.
Record any indispensable fork patch, evidence, rollback and retirement gate in
HERMES_LOCAL_PATCHES.md without changing the distribution release baseline.

## TS-382: causal qualification, then persistence-safe repair

Known: the original append_message exhausted a 60-second writer budget. Legacy FTS
triggers are bounded; a short real SQLite lock is waited out successfully. Neither
fact identifies the historical writer. The live state DB is not a stress-test fixture.

Bounded research: inspect exact write/maintenance call sites and use small sanitized
operation/timing metadata, not transcript text or credential/process-environment dumps.
Reproduce the candidate writer/append overlap in a temporary SQLite DB using the real
SessionDB paths. Scale the fixture to expose the mechanism deterministically; distinguish
an intentionally held generic lock from a reproduction of the product transaction.
Do not raise timeouts, kill processes, VACUUM/rebuild/backup the live DB, or infer a cause
from file size. Closed/unmerged upstream PR #100273 is a hypothesis source, not a fix.

Selected repair envelope after the causal gate: shorten the proven writer critical
section while preserving atomic visible transcript replacement, exact session/lease
ownership, concurrent append/watermark ordering, archived/search semantics, counters,
model metadata, error propagation and rollback. Move pure preparation outside the writer
transaction where sufficient. If bounded staging is actually necessary, reuse existing
visibility and lease boundaries, ensure readers see complete old or complete new data,
and define crash/cleanup behavior in Morfeo's research-result plan revision before build.
No new global queue, secondary persistence store, silent write drop, live DB migration,
unbounded retry, timeout inflation or full runtime rewrite is approved as a local choice.
The exact algorithm is deliberately not declared build-ready until the writer is proven.

The gate acceptance is an exact causal proposal plus pre/post oracle or a precise access
blocker. The issue acceptance is the repaired concurrency behavior, not that proposal.

## TS-275: real route qualification, then compatible boundary repair

Owners in the maintained fork: tools/vision_tools.py, agent/image_routing.py,
agent/codex_responses_adapter.py, agent/transports/codex.py. Offline evidence proves
byte preservation, not current-turn route selection or backend success.

Bounded research: recover effective routing from native turn context, not shell defaults.
Use only the already provisioned tool/client and credentials; do not print keys or add
providers. Make a small real baseline call with a valid synthetic image containing
image-only content; retain sanitized request-shape, response status/reason and correlation
metadata privately. A loopback server, HTTP 200 without image interpretation or a manually
forced unrelated model does not qualify the real route. Check the actual protocol/API
schema before assigning blame to an upstream backend.

Selected repair envelope after the causal gate: preserve image bytes, tool call identity,
response chronology and supported public tool interface. Correct the smallest proven
preparation/routing/adapter boundary. A protocol-specific normalization must preserve
semantics and remain isolated to that protocol; do not globally drop/replace image content
or silently change configured provider/model. Do not embed a secondary agent, acquire
credentials or edit a separate router product as an assumed prerequisite. If only external
backend entitlement/service changes can solve it, return the evidence and exact authority
needed; keep this issue open and continue the other repairs.

Morfeo records the exact payload/transport decision after the research result before the
new behavior is built. Real candidate qualification must interpret image-only content
through the operator's supported provisioned route, with the route explicitly evidenced.

## Integration and judgement

Supervisor chooses useful parallelism and owns tasks.md, shared-file ownership and
all native dependencies. The two research gates do not serialize already-qualified
binding/privacy/guard work. Fork source/patch ledger and Aether registry/policy files are
collision points to own or serialize, not a reason to duplicate frameworks.

Every implementation unit receives independent review, including evidence-only research
through the graph's native review lane. Supervisor consolidates known failures and
returns design-level non-convergence to Morfeo. Internal names and equivalent reversible
solutions within these interfaces are local freedom; product behavior, public schemas,
new authority or waived acceptance require the owning design decision.

Integrate reviewed commits without squash/amend/rebase. Run the declared full checks,
reconcile issue evidence, and safely adopt only relevant reviewed runtime changes using
the existing mechanism. Preserve unrelated dirty runtime files and active processes.
Close issues only when their actual acceptance is demonstrated. Keep release impact,
action and channel separate; no release or deployment is part of this objective.
