# Technical plan: contract and execution quality

Status: owner-approved approach; Morfeo-authored intellectual source. See `spec.md`
for outcomes and `quickstart.md` for acceptance. This is not Supervisor's task breakdown.

## Baseline and observations

Inspected Aether source: `115ec8ab9ed27140acee170b6f2e2cdc71df497e`.
Current Spec Kit evidence: `4a7341a93d944d6efe153b71da4a1adb9c2b578c`, refreshed
before design; see R2 research for exact source references. R0 constitution is unchanged.
The local ignored constitution is derived state; R0 remains its canonical source.

- `objective_contracts/store.py` checks required-section completeness and transport
  integrity, not intellectual sufficiency. Its schema and semantics remain unchanged.
- `resources/profiles/{morfeo,supervisor,implementer}/SOUL.md` owns portable role prompts.
- `resources/skills/` contains three existing canonical single-file procedures.
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

**D5 — Compatibility and rollback.** Do not weaken current ownership checks to accept
old or unknown bytes. Test baseline-to-candidate resource activation and restoration
of the matching baseline executable/resource state; never claim an arbitrary new
manager can validate an old bundle merely because its schema number matches. Existing
release validation binds resources to source bytes. No generalized cross-version
migration is authorized. If the existing reversible path cannot preserve private state
or safely restore the known baseline, stop activation and surface that concrete boundary.
Expected compatibility impact is additive (`minor`); final impact requires actual
package/rollback evidence. `release_action=defer`, `release_channel=none`: no tag,
package publication or release-version bump is required by this objective.

**D6 — Finite qualification adapter, not an unchanged harness claim.** Existing
`lab.runner.prepare_profiles` copies SOUL from its own imported package and only config
from `--profile-root`; it currently copies no canonical skills. The generic one-shot
runner also expects a successfully settled board and marks live outcomes as rolling
eligible. Merely passing two profile roots would therefore be an invalid comparison,
and generic PASS/FAIL is not the Q2/Q3 expected-defect oracle.

Add finite test support under `tests/qualification/contract_execution_quality.py`,
with fixed Q1–Q7 fixtures under `tests/fixtures/contract-execution-quality/`, reusing
native CLI/Project/board/dispatch primitives and existing test isolation. It is not an
agent tool, production module, daemon, generalized scenario engine or model evaluator.
The adapter's exact CLI, subject selection, evidence and case oracles are specified in
`quickstart.md`. Do not modify general live runner or evidence-schema semantics just
to make expected contract rejection count as product success. Keep results separate
from all rolling histories. Package materialization is tested through lifecycle,
while role behavior runs in fresh test-owned profile homes with verified subject
resources. Baseline and candidate have identical fixture intent and provisioned runtime,
provider/model/settings/capacity; only explicitly snapshotted approved resources differ.
Semantic judgment remains the existing independent Supervisor, not a new judge role.

## Ownership and writable surface

Morfeo owns this spec/plan/quickstart, standing R2/R3/R7 amendments, the Objective
Contract, and the authored meaning of the new skills and role wording. Supervisor owns
`tasks.md`, shared contract-supported execution decisions, independent review,
integration, qualification verdict and terminal closeout. Implementer owns the bounded
registration, fixtures, verification code and other application needed by its unit.
Do not assign exact-copying, staging or authoring the canonical Objective Contract to
Implementer. It is a read-only prerequisite already checkpointed by Morfeo.

Affected surface: three new skill resources; additive role wording; existing lifecycle
allowlist/materialization tests; existing package tests; scoped finite qualification
fixtures/checks; owning specs/guides/capability evidence/CI inventory. `AGENTS.md` needs
only a relevant navigation/operating correction if the actual change invalidates it;
the current generic canonical-discovery guidance remains valid. No new root skill index.

## Execution envelope

Owner-approved effects: local reversible work, tests, bounded role qualification through
existing provisioned access, independent review, normal commit/branch push/PR/checks/merge
and scoped resource activation after gates. No credentials or provider configuration may
be copied into public artifacts. Runtime selectors and exact local paths are private run
inputs, not this portable plan or the skill text. Do not modify another active objective.

Bounded qualification: one baseline and one candidate pass through Q1–Q7; at most one
corrected candidate rerun for each failed case. A failed case remains recorded; only a
corrected same-route pass satisfies it. Stop after that bound rather than add exceptions.
Use existing per-role concurrency and per-unit attempt/time limits from R7 without
increasing them; do not cancel a worker merely for taking time. Infrastructure capability
walls remain honest blockers, not failed reasoning or a license to repair Hermes here.

Readiness before dispatch: canonical artifacts and source resources exist in the exact
base; no material owner decision remains; the Project/envelope binding and intended
workspace are exact. Missing checkpoint visibility or a concurrently occupied primary
checkout does not authorize moving its branch, altering registry identity or routing a
root on the default board. Preserve the design and report that boundary if encountered.
