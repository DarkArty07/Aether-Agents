# Technical plan: contract and execution quality

Status: Morfeo-authored source; owner replaced synthetic qualification with organic observation in #317. See `spec.md`
for outcomes and `quickstart.md` for acceptance. This is not Supervisor's task breakdown.

## Baseline and observations

Inspected Aether source: `115ec8ab9ed27140acee170b6f2e2cdc71df497e`.
Current Spec Kit evidence: `4a7341a93d944d6efe153b71da4a1adb9c2b578c`, refreshed
before design; see R2 research for exact source references. R0 constitution is unchanged.
The local ignored constitution is derived state; R0 remains its canonical source.

- `objective_contracts/store.py` checks required-section completeness and transport
  integrity, not intellectual sufficiency. Its schema and semantics remain unchanged.
- `resources/profiles/{morfeo,supervisor,implementer}/SOUL.md` owns portable role prompts.
- At that inspected baseline, `resources/skills/` contained three existing canonical single-file procedures; this objective adds three more through the same explicit mechanism.
- `lifecycle.py::_CANONICAL_SKILLS`, `_skill_sources`, `_materialize_profile_bundle` and
  profile-bundle verification/materialization implement an explicit allowlist with
  hashes, marker-proven ownership, preflight and rollback. The current file contract
  is exactly one `SKILL.md` per canonical skill, not arbitrary support directories.
- Native Kanban already supports dependency-linked worktrees and concurrent workers.
  Audited records show three simultaneous Implementers in one objective and legitimate
  shared-file serialization in another. #251 documents overplanning before fan-out;
  those observations do not prove a missing dispatch primitive or measured speedup.
- `scripts/e2e/run.py` accepts a scenario JSON path and prepare-only/live modes. The
  existing laboratory supplies disposable fixtures, profiles and run evidence; its
  live lane requires an explicit existing executable/profile root and spend flag.

## Decisions and assumptions

**D1 — Three non-overlapping procedures.** Morfeo has personally authored the three
new `SKILL.md` resources in this candidate. Keep them standalone, with inline examples
and compact templates: this uses the existing distribution contract and avoids a
reference-file loader change. The unit-delivery template belongs only to the Supervisor
procedure; Implementer consumes it. Existing canonical procedures remain unchanged.

**D2 — Focused identity changes.** The candidate SOUL additions state outputs and
procedure discovery, not a complete manual or a per-project skill list. Preserve all
unrelated authority, routing, safety, recovery and publication wording. If concurrent
source has changed a SOUL, reconcile these additions semantically rather than overwrite
that file from an old base. Any newly discovered material contradiction returns to Morfeo.

**D3 — Existing distribution, no new selection mechanism.** Extend the existing explicit
canonical resource allowlist with exactly the three names. Continue the existing
all-role canonical-skill distribution; each role loads only the pertinent procedure.
Keep unrelated learned procedures private and untouched. Update existing package,
lifecycle, documentation and CI inventories/tests for the new explicit resource set.
Do not broadly allow arbitrary directories, paths, helper files or unowned collisions.

**D4 — Packaging boundary.** Morfeo-authored Markdown is intellectual input, not proof
that the existing Python allowlist already installs it. Implementer may make only the
necessary Aether resource-registration/inventory/test integration. No Hermes-core
modification, tool schema change, generic evaluator or scheduling machinery is needed.
A larger discovered requirement must be reported before expanding mutation.

**D5 — Compatibility and preservation.** Do not weaken current ownership checks to
accept old or unknown bytes. Inspect and preserve exact prior resource bytes and a
reversible restoration path; do not launch a rollback-test campaign in this session.
Never claim that an arbitrary new manager validates an old bundle merely because its
schema number matches. No generalized migration is authorized. If actual destination
ownership or safe preservation cannot be established, report that concrete boundary.
Expected package impact is additive (`minor`), not a claim of tested compatibility.
`release_action=defer`, `release_channel=none`: no tag, publication or version bump.

**D6 — Organic observation replaces the finite adapter.** The owner explicitly
removed the Q1–Q7 adapter, fixtures, baseline/candidate campaign and model probes from
current delivery. Do not implement or run them. The old design remains in Git history,
not as active work. Real later use is tracked in issue #317 without an evaluator,
watcher, cron job or automatic test campaign.

**D7 — Installation is bounded and inspectable.** Resolve the actual provisioned
profile home and owned resource destinations; inspect collisions and preserve unrelated
bytes before writing. Back up changed resources and read them back against the source.
This is file-operation verification, not an agent behavior test or permission to bypass
an ownership/approval refusal. No live board, session, credential or tool config changes.

**D8 — Report adoption separately from quality.** Record the installed revision and
exact changed resource paths in the delivery evidence and #317. Behavior remains under
organic observation; neither matching files nor the 52 historical tests qualify it.
Normal future sessions supply actual observations without forced fresh-agent probes in
this session. Existing processes may retain loaded instructions; do not restart them.

## Ownership and writable surface

The owner decides intent and every addition or change to role authority. `DESIGN.md`
and the owning R2/R3/R7 specifications retain their normative responsibilities.
Morfeo personally drafts this spec/plan/quickstart, the owner-approved amendments,
the Objective Contract, and candidate skill/SOUL wording; authorship grants no new
authority. SOUL resources express executable instructions within the approved roles,
not competing role definitions. Supervisor owns `tasks.md`, shared contract-supported
execution decisions, independent review, integration, qualification verdict and
terminal closeout. Implementer owns bounded registration, fixtures, verification code
and other application needed by its assigned unit.
Do not assign exact-copying, staging or authoring the canonical Objective Contract to
Implementer. It is a read-only prerequisite already checkpointed by Morfeo.

Affected surface: three new skill resources; additive role wording; existing lifecycle
registration; corresponding existing inventory expectations and documentation; scoped
resource adoption and ordinary file readback. No new qualification fixtures/adapter or
executed test campaign. The owner-stopped delegated route is not restarted by this plan. `AGENTS.md` needs
only a relevant navigation/operating correction if the actual change invalidates it;
the current generic canonical-discovery guidance remains valid. No new root skill index.

## Execution envelope

Current owner-approved effects: source registration and documentation reconciliation,
normal authorized repository closeout, scoped resource adoption and preservation/readback.
No tests or model-driven probes are executed in this session. Mandatory remote checks
are not bypassed; this is not authority to disable CI or broaden credentials. No credentials or provider configuration may
be copied into public artifacts. Runtime selectors and exact local paths are private run
inputs, not this portable plan or the skill text. Do not modify another active objective.

The former qualification budget is retired for this delivery. Future real objectives
retain their own test/authority standards and existing capacity; the organic tracking
issue does not spawn work or waive their gates. Infrastructure capability walls remain
honest blockers, not a license to repair Hermes here. Do not claim a measured speedup,
full-system PASS or validated compatibility from source adoption alone.

Readiness before dispatch: canonical artifacts and source resources exist in the exact
base; no material owner decision remains; the Project/envelope binding and intended
workspace are exact. Missing checkpoint visibility or a concurrently occupied primary
checkout does not authorize moving its branch, altering registry identity or routing a
root on the default board. Preserve the design and report that boundary if encountered.
