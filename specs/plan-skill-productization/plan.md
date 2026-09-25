# Technical plan: Aether-owned `/plan` (#504)

**Inspected base:** Aether `4ece53bfadfd0facbbea3220565841a74a07e97a`; selected executable maintained Hermes fork `aed6591a69f453a1867b73628603e7b53ba40ffc` (`0.20.1`). Source work and tests only: no live activation, release, fork change or service mutation. [spec.md](spec.md) owns requirements; this file owns the material shared design and remaining local implementation freedom.

## Baseline and deliberate decisions

- The owner-approved Objective Plan method already exists in `specs/r2-contract-and-handoff/spec.md` §3.1, `src/aether_agents/resources/skills/objective-contract-design/SKILL.md` and Morfeo's `SOUL.md`. The Aether skill named `plan` is the **user-invoked entry** only: project resolution, bounded plan-only writing and reference to the canonical method. It is not a second contract designer or a copy of the private learned skill.
- Hermes's selected `hermes_cli/commands.py` has no built-in `plan`. `agent/skill_commands.py:402-495` registers `name: plan` as `/plan` when it does not collide; its sorted same-name discovery means the local learned skill in a nested category must be explicitly tested against the package-owned root `skills/plan/SKILL.md`. This is a selected-runtime behavior gate, not a promise for all future Hermes versions.
- Source skill: `src/aether_agents/resources/skills/plan/SKILL.md`, with portable frontmatter, a single clear planning-only trigger and no private profile material. Native Aether release bundle installs `skills/plan/SKILL.md` **only in Morfeo**. The nine existing canonical skills remain available to each existing role as before. No new loader, registry, profile or core fork change.
- A plan is project-local, ignored by default, and stable per whole objective. Its anticipated Objective Contracts are revisable route markers, **never a cap**, authority transfer or automatic handoff; individual contracts retain R2/R7 attempt and convergence bounds. No plan generated for an unrequested simple question. A literal `/plan` request ends after planning.

## Candidate profile bundle and source-only boundary

`src/aether_agents/lifecycle.py` currently has one `_CANONICAL_SKILLS` list reused to write, hash, validate, activate, snapshot and uninstall the **same** set in each role. Existing release bundles (`profile-bundle.json` schema 2) contain per-role `skills` maps and release-lock digests. The new shape is deterministic:

| Release shape | Morfeo skills | Supervisor and Implementer skills |
| --- | --- | --- |
| Historical authenticated releases | Existing common set | Existing common set |
| New package candidate | Existing common set plus `plan` | Existing common set |

Material design requirement: use one coherent role-aware source inventory for candidate generation, wheel/sdist resource closure, deterministic profile-bundle SHA, disposable native materialization and candidate validation. Keep strict path, digest, duplicate-member, symlink, mode, role and resource-set checks; do not weaken an existing guard or rewrite historical manifests. The existing profile-bundle's per-role map can express the new shape without a new loader or state machine. Historical readback code already authored may be preserved if independently safe, but a release-transition qualification is **not** a gate to merge this source-only objective.

Candidate invariants to implement and exercise:

1. The candidate wheel and bundle agree byte-for-byte; disposable Morfeo homes receive canonical `plan`, Supervisor/Implementer do not. The native slash loader selects canonical bytes over a differently located learned skill.
2. A same-name learned skill and unrelated config survive disposable profile tests; no unowned existing path is silently overwritten. A malicious duplicate member or forged/cross-role resource still fails closed.
3. The selected installed predecessor may reject a direct candidate wheel because it expects the previous exact resource set. Document this as a limitation, **not** proof of a usable upgrade. Whether a bridge release, rollback or update sequence is needed belongs to a separately authorized activation objective. Do not run it here or make it block PR/merge.

Implementer may choose internal helper names and equivalent local layout; role sets, source integrity and preservation are the shared decisions. Keep existing valid candidate implementation without an unnecessary rewrite; focus remaining work on the skill, docs, targeted native/package checks and green integration. Do not invent a historical-release campaign or new global skill routing.

## Guidance and scope of documentation

`specs/r2-contract-and-handoff/spec.md` §3.1 now owns the explicit `/plan` obligation. `specs/r2-contract-and-handoff/research.md` records current Spec Kit and selected Hermes evidence and explains the deviation. Once the product surface is implemented and verified, reconcile `docs/guides/objective-plans.md` (replace the old generic-`/plan` distinction with installed/current-version guidance), `docs/authority.md` if its reader explanation needs a pointer, `docs/capabilities.toml` and the derived reference through `scripts/check_documentation.py`; explain that a skill is package-wide procedure but its **outputs live inside each selected project**. Update `AGENTS.md` only if a currently applicable instruction becomes false. Do not publish the private learned skill or operational `.aether/plans/` content.

## Verification strategy and route

Testing standard from this repository: `uv run --frozen` and pytest; CI also runs `scripts/run_tests.py` against the exact **public reference Hermes baseline**, docs/public-artifact checks, lint and wheel/sdist build. Native `/plan` dispatch is a **separate** qualification against Aether's exact selected maintained fork, not a result of that public-baseline suite. [quickstart.md](quickstart.md) owns runnable checks and expected observations. Verify candidate resource closure, role isolation, duplicate/forged rejection, learned-skill preservation and planning-only dispatch in disposable homes. Do not run old→bridge→new qualification or operate on live profiles/releases. Evidence must name the exact candidate revision and test producer; no invented full-suite PASS.

This objective changes packaging and role isolation; independent Supervisor review of source integrity and integration catches material failures that a direct one-file skill edit would miss. Morfeo supplies design and one finalized Objective Contract; Supervisor owns unit decomposition, independent review, integration and authorized PR closeout. A source merge does not authorize `release_action=publish` or `release_channel=stable`.
