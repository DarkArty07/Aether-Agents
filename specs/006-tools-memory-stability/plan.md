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

## TS-382: research gate satisfied; bounded publication design recorded

**Morfeo checkpoint: build-ready for U382F under the existing v1 contract.**
The approved research at `26f0a885287cb380d12c92d13ede992f2dcd6f7c` establishes
unbounded `archive_and_compact` publication as a causal writer class. Morfeo independently
reproduced the unchanged oracle: 2 failed/8 passed, with only the two legacy contention
cases failing. Historical holder identity is still unavailable and is not invented.

The normative repair algorithm, ownership/visibility boundary, exact batch policy,
concurrent-tail ordering, interruption/cleanup semantics and verification matrix are
recorded in [TS-382-design.md](TS-382-design.md), decisions D1-D7. It uses bounded
hidden staging in the existing database and one atomic metadata cutover, not a new store,
schema migration, queue or timeout increase. Ordinary appends must remain admissible;
the writer must not introduce a new target compression lock merely to stage rows.

This is the evidence-backed design revision explicitly reserved by v1, not a new owner
objective or weaker acceptance. The original finalized contract/digest remains in force;
no successor board or contract version is needed to satisfy this gate. Supervisor and
Implementer consume the exact committed checkpoint before resuming U382F, and retain
independent review plus integrated/runtime acceptance. No implementation or issue closure
is claimed by this design record.

## TS-275: research gate satisfied; auxiliary preparation design recorded

**Morfeo checkpoint: build-ready for U275F under the existing v1 contract.**
The approved research at `9245d435410eb23cf5a2f0fd29add94cc8c1f20e` separates the
historical external session-header episode (not repaired by this unit) from the real
remaining extreme-dimension rejection in the auxiliary vision path. Routing and
byte-exact adapter conversion are not the broken boundary.

The normative payload/preparation decision is [TS-275-design.md](TS-275-design.md),
V1-V5: reuse the existing 4-MiB encoded-data / 7,900-px embed policy proactively before
the first auxiliary request, only when a bound is exceeded, using the existing bounded
CPU executor and resizer. Already-compliant supported images remain byte-identical;
necessary rescaling preserves image meaning/aspect ratio and the existing scale note.
No provider/model/configuration/transport change or generic HTTP-400 retry is authorized.

This fulfills the evidence-backed design point reserved by v1 without superseding its
contract bytes, authority or acceptance. The exact reviewed three-fixture pre/post
oracle still requires real image-only content interpretation; a 200 status is insufficient.
Supervisor/Implementer consume the committed checkpoint before building and preserve
independent review, scoped runtime qualification and normal terminal closeout.

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
