# Finish usable launch and mixed-version lifecycle — bounded corrective design

Status: Morfeo design for the owner-authorized corrective objective; implementation and qualification are pending. This is not acceptance of the failed rc5 objective.

## Intent, baseline, and routing

The owner authorizes autonomous completion of the previously explained remaining work, without indefinite expansion: correct mixed-version lifecycle, remove observer-induced startup/history contention, document normal use, and qualify one local candidate. Runtime recovery already restored the installed rc5 and its launcher; do not repeat it or recreate its predecessor bootstrap campaign.

Inspected source baseline: `ee0aa036b2e0b70b137f761668209a5104f2e032` (merged rc5). Real predecessor evidence:

| Version | Exact Aether commit | Purpose |
| --- | --- | --- |
| rc3 | `d8ff984c67bfc147ac9c83cf8a34a72edc27c8df` | Frozen old reader lacking `tui_sha256`; negative legacy launch behavior |
| rc4 | `5a897746afe422f3c07f2290f9115d60204ef4d2` | Frozen old writer with exact-version branding |
| rc5 | `ee0aa036b2e0b70b137f761668209a5104f2e032` | Recovered live baseline and normal supported fallback |

Executable Hermes remains the maintained fork at `aed6591a69f453a1867b73628603e7b53ba40ffc`; its source digest remains `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`. No Hermes-fork change is authorized by this design.

Issue #485 is the canonical objective issue, with #488 and #490 the explicitly included observer/usability defects. Existing #480/#481/#482/#487 evidence is reused where artifact identity and criterion applicability match. #439's test-isolation lessons remain mandatory; do not repeat its live-unit pollution. #261 stable/publication/platform gates remain outside this objective.

Pipeline is appropriate because lifecycle and observation are separate responsibilities with independent implementation/review, followed by cross-version integration. Morfeo owns this material design; Supervisor owns receipt, shared execution decisions, decomposition, independent review and closeout. No new orchestration framework is needed.

## Confirmed failure mechanisms and limits

1. Installed rc4 `projection_spec` and `project_release` select branding by `record.version == "1.0.0rc4"`; a rc5 target receives the legacy launcher. Source-manager execution does not acquire target semantics when a pointer changes.
2. Newer `ReleaseRecord` adds `tui_sha256`. `_commit_active(asdict(record))` writes the new field into an old target's pointer. Actual rc3 `ReleaseRecord.from_json` rejects it, even when null. Schema number equality is not evidence of reader compatibility.
3. `tests/test_hermes_gateway_service.py:923-995` at the baseline uses one new manager with version-labelled records and replacement validators. It is useful unit coverage, not proof of old/new executable compatibility.
4. `_Observer.__init__`, `_collector_for_project`, `_restore_all_retained_bindings`, `_retained_trace_exists` and native reconciliation repeatedly validate retained history. A clean installed TUI reached ready after 7m36s on the accumulated local corpus; it was slow, not permanently deadlocked. `query._ingest_for_query` separately collapses busy/incomplete catch-up into a generic unreadable error through `brief.observe`. In-process busy contention is a hypothesis to reproduce, not an already-proven exclusive cause.
5. Existing rc5 `recover()` can reconcile its active projections. Do not assert that recovery is impossible or expose another writer merely because the public reserved `reconcile` parser is incomplete.
6. The prior `observation_state_preserved: true` receipt is a code constant, not a complete measurement. Presence counts and expected projection digests are not actual before/after content witnesses.
7. Frozen rc3 does not contain the modern packaged launcher. Never claim that restoring rc3 pointer readability gives it a feature it never shipped.

## L1. Target-compatible activation record

Decision: the immutable target `record.json`, validated against its release lock/wheel/installed fingerprint, owns the active-record field shape. The source manager must not serialize its own dataclass defaults into that pointer.

- Retain the exact target-owned field set and values, with only the existing transition-owned `previous_release_id` updated to the actual predecessor. Preserve optional-field absence versus explicit null; do not drop arbitrary unknown keys as a recovery shortcut.
- Before any pointer/projection mutation, run the proposed active record through the exact target manager's reader in a bounded, isolated subprocess. Confirm target release identity and installed-record coherence, not only JSON parsing. A target that cannot prove its record semantics fails before cutover.
- Parent source manager retains the existing lifecycle lock, journal, source authority, CAS and compensation responsibility. Pure target-reader preparation must not acquire that same cross-process lock or mutate live state.
- Compensation restores the exact previously captured active-record bytes, not a reserialized version using the failing target/source class. Record and selector recovery remain paired; no successful receipt precedes target-side validation.
- Do not edit frozen rc3/rc4/rc5 artifacts, loosen old readers, or change the release-lock schema to hide the regression.

## L2. Target-owned projections and bounded reconciliation

Decision: the target's authenticated Aether code determines the launcher/Desktop/WSL projection bytes. Reuse the existing target-interpreter subprocess pattern used by `observation/projection_transition.py`; do not confuse its observation read-model pointers with filesystem launch projections.

The corrected source manager prepares a bounded target projection plan before cutover, using fixed operations and allowlisted managed destinations. The target plan supplies opaque file bytes/digests and the target active-record representation. No request accepts an arbitrary executable, shell command, method name or unverified destination. Parent validates bounds and destination ownership, journals prestate, commits with CAS, applies the plan and validates from the selected target. Private helper names/file placement are implementation freedom; the source/target responsibilities and checks are not.

Hermes continues to own its main gateway unit. Service install/refresh goes through the selected Hermes CLI only when the operation requires it; target projection preparation does not call service operations. Rollback preserves opaque prior unit bytes on compensation. No systemd drop-in, observer disablement, byte-ownership conflict or restart loop is introduced.

The existing normative `aether reconcile --to active [--dry-run] [--yes] [--json]` surface may be completed ONLY for bounded reconciliation of the already active, authenticated release. It must not select another release, install packages, invent authority, restart a service when read-only/no-restart reconciliation suffices, or implement `--to installed` as incidental scope. Unsupported modes remain explicit. Its preview is non-mutating. This exposes existing recovery behavior rather than requiring a knowingly failing update command or an operator Python script.

Legacy boundary:

- The first live promotion starts from recovered rc5, never rc3. Rc5's known branded/TUI shape is compatible with the next RC; prove that exact first hop in isolation before relying on it.
- Frozen rc4 cannot be made to execute a new writer by a source patch elsewhere. Reproduce its wrong projection in isolation; where an already prepared/activated new target can authenticate itself, its explicit active reconciliation must finish the legacy handoff without record edits. Clearly report that legacy two-step behavior; never call the old command's `changed` receipt whole-flow success.
- Old rc3 reader compatibility must be proven with real old code and target-shaped serialization. A requested legacy transition that cannot prove target integrity and a supported operator-visible disposition must be refused before mutation, not completed broken. Such a refusal is reported as an unsupported legacy route, never a passed rollback. It does not retroactively satisfy the failed rc5 contract's literal rc3 criterion.
- Required successful end-to-end release cycle for this objective: exact recovered rc5 -> corrected candidate -> exact rc5 -> corrected candidate, in an isolated store. Field-addition regressions also use actual rc3 readers, not emulated dataclasses. Do not promise unlimited future/backward compatibility.

## O1. Passive observer startup and retained-history work

Decision: reuse the plugin-owned reconciliation worker and existing journal validation/read model. Registration and synchronous native hooks must not replay retained journal history, wait for history recovery, or hold the maintenance lock. They install hooks/tools and record bounded events as already specified by OBS-D-027/OBS-FR-082. Do not replace validation with trust in unvalidated local bytes.

- Restore retained bindings asynchronously. Until a binding is verified, report existing incomplete/unresolved coverage rather than attributing events to a guessed trace. Capture and flush remain available; verified native/canonical bindings can proceed independently of slow historical catch-up.
- Build/reuse one validated retained-evidence index per catch-up snapshot, covering needed trace existence and binding rows; do not rescan all events once per task, token or trace. Reuse existing validated projection/cursors where their provenance suffices. Keep journal generation/offset/identity with any derived cache, invalidate on replacement/truncation/schema change, and preserve valid-prefix/quarantine/privacy rules. Persisted storage, if needed, stays under the existing project-derived observation store, never a new authority database.
- Yield/cancel work through the existing worker stop/debounce boundaries. No thread or hidden operation survives unload indefinitely; no completed historical replay is repeated when the retained snapshot is unchanged. Live appends are incorporated incrementally without caching an unvalidated tail as authoritative.
- Neither graph updates nor model/network requests belong in observer startup/catch-up.
- Foreground launch must reach real agent-ready without waiting for a deliberately paused historical scanner. Native hook performance retains the existing canonical p95 <=5ms / p99 <=20ms gate, and existing reduction gates remain unchanged. Measure actual retained-corpus startup separately; do not invent a universal total-TUI latency SLO or count a rendered shell as agent-ready.

## O2. Native observation query parity

Prove the in-process failure while capture/reconciliation are active before attributing a cause. Native tool and CLI must resolve the same explicit project/ref and validate the same summary semantics.

Decision: keep current success/empty schemas and privacy limits. Distinguish known bounded busy/incomplete catch-up conditions from genuinely unreadable state using typed internal errors and bounded fixed public codes: native `AETHER-OBSERVE-BUSY` / `AETHER-OBSERVE-CATCHUP-INCOMPLETE`, CLI `STATE_BUSY` / `CATCHUP_INCOMPLETE`. No raw exception, path, payload or lock owner escapes. A retryable error is not a successful or fresh summary. Existing genuine unreadable/integrity refusals remain fail-closed.

Do not extend the current 60-second catch-up and two-second lock-wait limits, add polling daemons, or satisfy parity merely by renaming the error. Under a valid settled snapshot the registered native tool must actually return the validated brief, including inside a real new TUI session; under controlled contention return within the bound with an honest fixed code, and succeed once contention clears. Any different material root cause requiring architecture/scope change returns to Morfeo; local equivalent fixes remain implementation judgement.

## U1. Preserve and teach normal launch

Keep exact project selection, no name/recency inference, and no new default-project UX. Teach `aether` within an initialized project; `aether --project PATH` anywhere; fresh/Continue actions; `--resume latest`; visible ambiguity; optional `AETHER_PROJECT_ROOT` selection and its precedence over cwd. Give Bash/Zsh and Fish examples AND removal commands with generic paths. Aether does not silently set a personal shell preference. The owner's existing local preference is preserved and never published.

Include clearing inherited transport selectors (`HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, and stale active-session transport paths) when launching a new release; a nested old TUI must not silently start the old backend. Bind the target interpreter/source/TUI after scrubbing. Do not scrub unrelated provider credentials or change model/tool configuration. Fresh and resume launches must be qualified with both a clean shell and contaminated old-process transport environment.

## Verification and evidence

Apply CONTRIBUTING.md's locked focused/full pytest, Ruff, format, mypy, documentation, coverage and wheel/sdist gates. Focused iterations precede the integrated full run; reuse exact unaffected evidence, never rerun a large campaign for ceremony. No lowered thresholds or tests skipped to get green.

Use one reproducible qualification entry under existing scripts/fixtures (its name is Supervisor-owned), with exact artifact/revision inputs and receipt output. It must be runnable without the live installation. Resolve real target Python/import paths and hashes in each subprocess. A same-process fixture with version strings and replaced readers/writers is never the decisive oracle.

Isolation is an acceptance prerequisite: distinct HOME, XDG data/config/state/cache, TMPDIR, HERMES_HOME, project/board registry and all HERMES_KANBAN_* routing; no inherited live D-Bus socket or systemctl side effects. Use explicit test controllers for the service boundary and real provisioned Hermes CLI generation under disposable destinations; label mocked OS supervision versus real installed-package behavior. Hash/inode/mtime witnesses prove the live unit, active pointer and operator configs were untouched by tests. Do not run unsafe fixtures against the real user paths.

Required scenarios:

1. Reproduce both original defects with frozen old artifacts; corrected writer produces a target-readable active record without adding absent fields, and target-generated projections match the target's own expectation.
2. Exact rc5 -> candidate -> rc5 -> candidate succeeds; failed target parsing, projection generation, service materialization, restart and interrupted compensation never leave a false successful/pending half-state. Test old-record/unknown-newer cases explicitly.
3. Legacy rc4 writer produces its recorded wrong projection; active target reconciliation repairs it through the supported command when its prerequisites hold. Unsafe legacy routes fail before mutation and are documented, not reported green.
4. Plugin registration and foreground tool/session callbacks complete while a historical reader is held on a barrier. Stress retained evidence with unchanged, appended, replaced, truncated, conflicting and quarantined segments. Validate binding/privacy invariants and full-vs-incremental semantic equivalence.
5. Native status/changes/diagnose and CLI parity under concurrent capture, lock contention, backlog, valid settled state and genuine corruption. Show real success after clearing temporary contention.
6. Installed fresh and resume PTY startup with exact target backend/profile/project, including polluted transport environment; no npm/build or locked-source drift. Record time to actual agent-ready and one minimal live response through already provisioned access, with no model/provider changes.
7. Public usage examples/help/documentation checks use generic paths and exercise ambiguity/default override/unset behavior.

Before live promotion require independent approval of the mixed-version fixture results, integrated candidate gates, reviewed green PR merge, exact local-only annotated candidate tag and non-mutating update preview. One controlled activation window may restart the Aether gateway; do not explicitly kill the owner's unrelated/current TUI group for convenience. Inform the originating session before an interruption and preserve durable receipts outside the gateway cgroup. Keep the existing TUI until a new candidate TUI is confirmed. A native gateway restart stability check is part of that window. The only live fallback is the preverified coherent rc5, once if necessary; rc3/rc4 experiments remain disposable.

Readiness, source/TUI digests, actual pre/post config hashes, unchanged unrelated services, session/board identity continuity and accepted expected new records are separate witnesses. Do not equate all user-state bytes with immutability while the system is running. No secret or session content in public evidence. Prior structural/semantic Graphify evidence may be reused at unchanged code identity; refresh the final revision as its canonical procedure requires, reporting pending/cancelled honestly without a semantic-model retry campaign.

## Unattended execution and origin-session preservation

The owner reaffirmed unattended execution within this objective. Routine technical and execution decisions stay delegated to Morfeo and Supervisor; this is not authority to expand scope, weaken acceptance, widen credentials or bypass a protected edge. The following operating disposition applies to the remaining execution without changing the finalized contract or its pre-live gates.

- Preserve the originating TUI throughout the unattended window, including after a new candidate canary is ready. Do not close, restart or signal it, its terminal shell, or its process group. End only purpose-created canary processes by their exact verified handles. Retain the release files used by the originating process.
- Every authorized interrupting step must run from a durable runner independent of BOTH the originating TUI and the gateway process trees/cgroups. Persist phase, exact identities, prestate, results and fallback instructions in private evidence before starting. Verify that the runner is actually independent; a background child of the TUI or gateway is not sufficient.
- The pre-interruption notice is informational for an already-authorized operation, not a new requirement to wait for an owner reply. Do not start cutover until isolation, exact-version qualification, review, merge and fallback gates pass. If the supported transition cannot preserve the origin session, defer that live effect with a precise blocker rather than forcing the session closed; continue safe independent work.
- After interruption or redispatch, inspect the actual selected release, durable phase/exit receipts and transition journal before resuming. A missing PID or a delayed notification does not authorize replaying an update or rollback. Existing single-window and single-qualified-fallback limits remain unchanged.
- Send unresolved implementation/design questions to Morfeo through the existing collaboration route. Escalate to the owner only for authority or product decisions not already delegated, or a protected-edge/runtime failure that cannot be resolved within the existing boundaries. The seven-hour checkpoint still reports exact progress without killing healthy work or silently adding scope.

## Convergence and closeout

Use parallel implementation where responsibilities are disjoint; keep shared lifecycle/serializer/projection changes in one owning unit. Supervisor determines the minimal task graph, with documentation and qualification supporting—not duplicating—implementation. No new boards/contracts for ordinary rework, no synthetic observer adoption campaign, no permanent watcher, no issue-backlog cleanup.

The previous 4–7 hour estimate is a planning range, not a guarantee or acceptance percentage. Use seven hours from root claim as a progress checkpoint: if unfinished, deliver a compact exact blocker/remaining-work update rather than silently extending scope. Do not terminate a healthy worker or an atomic operation merely because that time elapsed. Repeating the same failing root cause without new evidence requires a bounded design intervention; it does not authorize another live cutover.

One local candidate identity is `1.0.0rc6` / `1.0.0-rc.6` / `v1.0.0-rc.6`. Verify absence before creation. Develop/review the candidate before tagging; no per-iteration release/tag and no moving existing tags. Compatibility conclusion is patch; action prepare; channel prerelease. No public package/release/tag push or stable claim.

Terminal closeout reuses supported continuation/evidence without editing completed historical boards. Morfeo performs result reception against actual artifact and criteria. Close only evidenced issues; report remaining gates without inventing acceptance. Clean only this objective's merged branches/worktrees after evidence is durable, distinguishing the old retained investigation residue. Finish when the declared scenarios pass; do not add ornamental refactors or another review round.

## Research provenance and adaptation

GitHub Spec Kit inspected directly through upstream contents at refreshed commit `d4229c071c7ea3885b43e8a7739847300f618f13`: `templates/commands/plan.md:64-72,114-157,163-164` requires resolving unknowns, constitution checks and a runnable validation guide; `templates/commands/analyze.md:54-60,108-113,131-145,174-190` supplies read-only consistency/coverage review. Adopt that intellectual contract. Do not vendor its code or run its extension hooks. Aether's gap is unattended role assignment: Supervisor performs receipt/decomposition/review and Morfeo resolves material design findings instead of waiting for an interactive command recommendation. This is the existing adaptation, not a new methodology.

Relevant owning artifacts: DESIGN.md; specs/r0-design-governance/spec.md; specs/001-aether-v1-productization/spec.md and contracts/cli.md; specs/002-aether-contract-observation/spec.md (OBS-D-027, OBS-FR-050/082 and existing performance gates); previous objective oc_a7a3cff05e82c148@v1. Private recovery/diagnostic receipts are local evidence only and must not be copied into public files.
