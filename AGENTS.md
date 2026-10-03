# Aether Agents repository

This repository contains Aether's public product source, versioned policy, canonical specifications, and reproducible configuration. The current build target is the Aether 1.0 contract in `specs/001-aether-v1-productization/`; a design decision or local candidate is not evidence that a package, release candidate, public service, or stable release exists.

`DESIGN.md` is the canonical conceptual design for the current redesign. It defines the intended roles, authority boundaries and fixed high-level product decisions. Technology choices not explicitly fixed there remain undecided and must not be inferred or implemented without an owner decision.

Live Hermes profiles and other runtime state under `home/` are local evidence only and must not be committed. Keep credentials, sessions, databases, memories, logs, boards, repositories, owner identifiers, machine paths, and private provider/model/router bindings out of public artifacts. For the complete reader-facing placement and conflict-resolution map across all artifact classes, see [`docs/authority.md`](docs/authority.md).

The accepted product has three roles: Morfeo, supervision, and implementation. Implementation is replicable in parallel instances. The accepted design and A1 contract still grant no authority by themselves to create or activate profiles, start workers or services, invoke models, acquire credentials, publish, deploy, cut over an installation, or perform another protected external effect.

**Current stabilization authority (PD-71 through PD-74, 2026-08-26):** ordinary local/reversible work is governed by scope, worktrees, Git, tests, review and rollback rather than role micro-permissions. The pre-tool hook is restricted to high-confidence secrets/credentials, credential acquisition/widening, unauthorized remote/external mutation, and clearly destructive irreversible effects, plus one contract-directed integrity guard: a `kanban_create` whose `title`/`body` ends in a transport truncation sentinel is refused before persistence (`specs/007-session-residual-stability/spec.md` §SR-227), which is not a role or permission decision. Morfeo recovery is rollback-first and bounded; Implementer owns local technical judgement; Supervisor may make small integration repairs. Feature expansion and nonessential Hermes changes remain frozen until the rolling E2E reliability gate passes, except for explicitly owner-authorized bounded objectives. The former Telegram Monitor implementation/activation exception is withdrawn by the owner-directed retirement below; its specification and evidence remain historical and do not authorize reactivation.

**Owner-directed Lab/Monitor retirement (2026-09-28 UTC):**
`specs/lab-monitor-retirement/spec.md` and revised PD-75 own the removal of the formal
Lab, Telegram Monitor and its periodic reports, without a replacement. Preserve native
Hermes cron, ordinary Telegram interaction/native execution notifications and all other
functions. Minimal isolation support needed by surviving tests belongs in test support,
not a renamed product Lab. This objective authorizes autonomous implementation and
normal reviewed source closeout, not a release, live activation, state purge, provider
probe or agent-behavior campaign. PD-74 remains outstanding; deleting tooling is not a
reliability PASS. Use this objective's plan/quickstart for preservation checks and keep
prior failures/releases immutable.

**Owner-authorized external Implementer harness (#563, 2026-09-30 UTC):**
`specs/external-implementer-harness/spec.md` and amended PD-40 own an opt-in Claude Code
executor for Implementer work attempts, selected only when the owner explicitly requests
it for a contract; Hermes remains the default executor for every role and the board the
only inter-role transport. This is the explicit PD-74 bounded exception: it authorizes
autonomous implementation, isolated real Claude Code runs and normal reviewed source
closeout. On 2026-10-03 the owner directed its direct completion, integration into
`main`, the next release candidate and the local update (spec OD-11); that release and
update belong to the separate RC19 record (adopted through an RC18 bridge). It never authorizes a Hermes fork change,
Claude credential handling or an agent-behavior campaign.

Only Morfeo has a proper agent name; supervision and implementation remain role descriptions. Hermes Agent and GitHub Spec Kit are selected foundations. Aether reuses native Hermes profiles, Projects, boards, worktrees, review, and lifecycle where they qualify. A2A remains available but unused under R6; framework availability never authorizes an integration mechanism.

Executable Hermes source is Aether's maintained fork `DarkArty07/aether-hermes` branch `aether-main`, bound by release-lock source mode `maintained_fork` — emitted as `schema_version` 5 with the closed `hermes.extras` allowlist and readable as schema 4 — through repository, exact commit, source-tree digest, artifacts and provenance, and installed through `aether update`. The earlier fixed public baseline `NousResearch/hermes-agent` `v2026.8.18` — annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution `hermes-agent` `0.20.4`, Python `>=3.11,<3.14` — remains a reference baseline for upstream-compatible behavior and historical evidence, not the deployment input. `.patch` files and HLP records are audit/reconstruction evidence and are never replayed onto the active runtime; the retired `transitional_fork` mode is refused for new preparation. Hermes keeps its own distribution identity (`hermes-agent`). No new Aether capability may depend on a downstream-only core change, and each accepted fork change retires when an exact released upstream artifact passes its behavior gate.


## Historical objectives (earlier owner authorizations, no longer current authority)

These entries are preserved, dated history from objectives that have already
delivered their source into this `main` branch. They retain their links and
preservation gates, but they are **not** standing authority for new work: nothing
below authorizes new implementation, a new release candidate, runtime activation or
an external effect today. Each objective's own specification, Objective Contract and
release evidence remain the authoritative record of what it did. For where this
repository currently stands, read [`README.md`](README.md) and the stabilization
statements above; [`CHANGELOG.md`](CHANGELOG.md) records what each release actually
shipped.

### RC15 review maintenance (delivered 2026-09-25)

Superseded as authority by the later RC17 candidate and the subsequent `main` source; kept for its boundary language (resource checks are not agent-behavior qualification).

The current owner objective prepares RC15 with the revised Supervisor SOUL and
canonical review procedure. Its Hermes source is the RC14 base plus a generic
read-only count of recorded review returns in task context. Aether still works when
that optional context field is absent by consulting existing durable history; no
workflow decision or enforcement mechanism depends on the addition. The objective
excludes agent behavior tests and unrelated deferred fork changes. RC15 does not
resume or accept the paused #494 objective. Preserve earlier releases and distinguish
focused deterministic checks, packaging verification and untested agent behavior.

### Role-guidance maintenance (#426 / #459, merged 2026-09-26)

The role SOULs and canonical skills it authorized now live in the packaged resources referenced above; its instruction-maintenance scope is not a precedent for a further documentation objective without new owner authority.

The owner authorizes Morfeo to directly consolidate the three package-owned SOULs and
relevant canonical skills, preserving intent, useful contract boundaries and proportional
verification. This is instruction/source maintenance, not a pipeline or release. Close
#426/#459 after source integration and documentary/resource checks; no E2E, synthetic
agent campaign, live canary or runtime adoption is part of this objective. The owner will
observe ordinary usage and reopen issues if needed. Do not report behavioral qualification
from resource checks. See `specs/006-contract-execution-quality/spec.md` for the owning
maintenance decision; this does not waive required repository checks or unrelated gates.

### RC6, RC8 and RC14 candidate objectives (delivered source)

Each candidate below delivered its own source revision, which is recorded in
[`CHANGELOG.md`](CHANGELOG.md). Their installation-specific pins and local-only tags
describe that objective's own lane at that time; they are not the current runtime pin
and authorize no new effect.

The RC6 bounded corrective objective is `oc_b5926701207812e8@v1`, designed in `specs/001-aether-v1-productization/plan-rc6.md`: finish mixed-version lifecycle compatibility, observer startup/native-query reliability and portable launcher guidance, then qualify one local candidate `1.0.0rc6` / `1.0.0-rc.6` / `v1.0.0-rc.6`. Its conclusions are `release_impact=patch` / `release_action=prepare` / `release_channel=prerelease`; the annotated tag remains local-only, never pushed. This is not stable `1.0.0`, PyPI publication or WSL2 qualification; #261 stays open. #485 is the owning objective issue, with #488 and #490 included and related launcher/service issues reconciled only against actual evidence. The failed rc5 contract `oc_a7a3cff05e82c148@v1` remains non-accepted history; operational recovery does not retroactively accept it. Exact frozen old readers/writers must be tested in isolation before live effects, and coherent rc5 is the only live fallback for this objective. Executable Hermes stays at maintained-fork merge `aed6591a69f453a1867b73628603e7b53ba40ffc` (`#450`+`#461`) for this objective's own lane, and that commit remains the installed runtime pin. The separately authorized #494 source phase advanced the maintained fork's `aether-main` to `58f8c37a49b341f25b8fdd6310542fe932031b8d` with reviewed source, a portable artifact and reconciled evidence only; its live adoption is a deferred successor, not a runtime change. The separately authorized source repair for issue #433 then advanced the same branch to `621047dc1c10cceb2825013cc8bb611b4d0e8de1` (reviewed auxiliary Responses reasoning-usage preservation, portable artifact and reconciled evidence only); its live adoption is likewise a deferred successor and the installed runtime pin named above is unchanged. Existing rc.2 through rc.5 tags and activation records remain immutable; the published-but-rejected rc1 (`oc_3397f9f05d780f8e@v1`) must not be activated. Automatic deployments to the existing Aether GitHub Pages site caused by reviewed green merges required by this objective remain authorized; no manual Pages dispatch, other target or unrelated deployment is authorized.

Current owner-authorized local maintenance for #497/#495 is a two-candidate managed update. RC7 is the compatibility bridge with RC6-identical Morfeo SOUL and canonical contract skills; this `1.0.0rc8` source revision restores the #495 planning guidance and the #497 updater repair. For #487, the owner's accepted option B gives Hermes ownership of the complete main gateway unit; Aether verifies only its required service invariants, as reconciled in A1. Source or a local tag alone cannot establish qualification, active runtime selection or improved agent behavior: require reviewed Git evidence, exact-version isolation and a verified managed cutover. No tag is pushed or published. These maintenance candidates do not accept the outstanding RC6 objective, qualify stable release or WSL2, or authorize unrelated runtime changes.

The owner-authorized Morfeo MCP objective (#515) continues in this `1.0.0rc14` source candidate. It keeps rc13's schema 5 emission, `hermes.extras: [mcp]`, and `aether mcp morfeo serve`. Candidate preparation qualifies required HLP coverage at the executable Hermes pin `aed6591a69f453a1867b73628603e7b53ba40ffc`; HLP-428 and HLP-433 stay deferred and are not retired. This source is not an activation claim. No Hermes fork change, tag push, or stable release is authorized.

## How Aether is built: borrow the thinking, write our own workflow

**Read this before designing or building anything.**

Aether is not inventing software-engineering methodology. GitHub Spec Kit has already solved the intellectual part — how to turn intent into a specification, how to keep a specification honest, how to check that requirements are well written, how to detect drift between intent and code, how to converge. Aether's contribution is a **personal multi-agent workflow built on top of that thinking**, not a competing methodology.

So the working order is always the same:

1. **Look upstream first.** Before designing a mechanism, check whether Spec Kit already provides the thinking. Most of the time it does, and it is better than what we would produce in one session.
2. **Read the actual file.** Cite the path, the line range, and the inspected revision. Never repeat a claim about upstream behavior from another artifact, another agent, or memory. Secondhand claims have already caused wasted design work in this project.
3. **Reuse the intellectual contract, not the plumbing.** Adopt the reasoning, the artifact roles, and the quality standards. Do not vendor the code, fork the core, or assume a mechanism is wanted merely because it exists.
4. **Design only the gap.** Write down what upstream genuinely does not cover, and why Aether needs it. That list is usually short. If it looks long, the upstream reading was too shallow.
5. **Record every deviation.** When Aether departs from upstream, the reason goes in the owning stage's research artifact, so a future Spec Kit upgrade can be reviewed against a stated rationale rather than rediscovered.

### The recurring adaptation

Spec Kit assumes a human is present. Its commands end by recommending a next step to that human, its clarification loop is interactive and capped, and its checklists are reviewer-owned.

Aether's owner is deliberately **absent** during execution. So the adaptation is nearly always the same single move:

> Where a Spec Kit command would stop and recommend a step to a human, Aether must have already decided which role takes that step unattended.

That is the shape of most Aether-specific design. It is not a rewrite of upstream behavior — it is a decision about who acts when nobody is watching.

### What this is not

This is not permission to weaken Spec-Driven Development. Adaptations may redistribute work across roles, remove assumptions about human presence, and add authority or budget that upstream has no reason to carry. They may not quietly drop a normative principle because it is inconvenient for automation.

Worked examples of this method live in `specs/r2-contract-and-handoff/research.md`, which records what upstream already solved, the three gaps that remained, and why.

This principle is owned canonically by `specs/r0-design-governance/spec.md` and is materialized locally for Spec Kit at the ignored `.specify/memory/constitution.md`; the local copy is not a second authority.

## Project guidance and canonical skills

**Local release (RC19, #564, owner-directed 2026-10-03):** the owner directed finishing
#563, integrating it into `main`, preparing the next candidate and updating the local
installation. One local RC19 candidate, its local RC18 adoption bridge, immutable local
annotated tags and the two managed local cutovers are authorized. The exact fork pin is
`66e87f3487d75cda3681146818006b7c796a71a9`: RC17's selection plus HLP-554, the reviewed
source of the Codex message-id guard that the installed RC17 carried as a live edit
(#554, #560). It reuses #563's full gate and isolated real run plus the normal required
PR checks. No tag push, public release or agent campaign is authorized. RC17's frozen
manager accepts only the historical package shape, so the bridge keeps that shape and
carries RC19's manager; see `specs/rc19-local-release/spec.md`.

**Historical local release (RC17, #542, prepared 2026-09-27):** source integration and
one managed local cutover are authorized with bounded verification, reusing reviewed
fixes and required CI rather than duplicating a full local suite or creating an agent
campaign. The exact fork pin is `007cfb77676b6b024d2c0986f4585e6cfdcf18d6`. The public
skill is `aether-plan`, but its internal `skills/plan/` key is retained for RC16 reader
compatibility. Preserve private configuration and RC16; no tag push, public release or
live rollback rehearsal. This separate release supersedes earlier candidate-local fork
deferrals only for its own lane; see `specs/rc17-local-release/spec.md`. Historical
evidence and the #541 delivery below keep their original limits.

**Historical bounded maintenance (#541, 2026-09-27):** the owner authorized direct
Morfeo instruction and documentation work for portable project methodology, expected
behaviors and the `aether-plan` rename. Review the actual diff and affected references
only; do not run test suites, builds, linters, additional validation campaigns or CI
for this local delivery. The minimal resource-name registration and test/reference
reconciliation needed by the rename are in scope. No pipeline, runtime activation, publication,
workflow disabling or protected-check bypass is authorized. This objective-specific
boundary is recorded in R2 §3.1 and `CONTRIBUTING.md`; other objectives retain their gates.

Use the project-adoption and predesign entry of `objective-contract-design` when
establishing or reconciling project guidance. Transfer the methodology, not this
repository's content or history. Product code, tests, specifications, technical plans,
research and documentation stay outside `.aether` in the project's established structure.
Aether identity, finalized contracts and project procedures retain their existing
`.aether/project.toml`, `.aether/objective-contracts/` and `.aether/skills/` conventions.
Local drafts, plans and exploratory observations are ignored by default; `.aether`
is neither wholly disposable nor wholly public. Preserve other harness instructions
and tool-managed runtime, worktree, cache and external research locations.

For unresolved exploration that warrants continuity, use one descriptive
`.aether/observations/<topic>.md`. Separate sourced facts, hypotheses, questions,
decisions and continuity; the note is not an accepted requirement or execution authority,
and is unrelated to runtime `aether observe`. Transfer enduring decisions/evidence before
retiring only an eligible owned resolved note. Put discretionary project scratch under
`.aether/tmp/<work-scope>/`, not throughout the repository root. Create only useful
artifacts; no required empty tree, bulk migration or blanket cleanup follows from these
conventions. See R9 §3.1 and [project adoption](docs/guides/project-initialization.md#methodology-after-initialization).

The [expected-behavior guide](docs/guides/expected-behavior.md) explains meaningful
instruction triggers, limits, sources and observable signs. Reconcile affected entries
when changing those expectations; the guide is not another authority or proof of
compliance. Source instructions, installed wording and observed conduct remain distinct.

For objective planning and cross-session continuation, see
[`docs/guides/objective-plans.md`](docs/guides/objective-plans.md) and the
`objective-contract-design` canonical procedure's planning entry. Keep one local
`.aether/plans/<objective-slug>.md` when a meaningful route or continuity is needed;
do not select by recency, duplicate canonical obligations, or add plan ceremony to
simple bounded work. Plans remain local/ignored unless publication is explicitly
decided. A session or contract boundary does not reset failed approaches or the
reasoning needed to justify continuation. Source instructions do not prove live adoption.

The explicit Morfeo planning entry is `/aether-plan`, using the canonical `aether-plan`
skill and stopping after planning without implementation, contracts, cards or workers.
Generic `/plan` is not an alias. Reuse relevant observations as attributed context,
without treating hypotheses as approved scope. The source rename does not establish
that an older running profile already exposes the new command.

Every project root has operating guidance. Morfeo establishes missing root `AGENTS.md`
guidance only after inspecting the repository and confirming its constitution; `aether init`
does not invent generic project content. Existing brownfield guidance is preserved and
reconciled, not overwritten. The role whose authorized change invalidates an operating
instruction updates it in that same change, and Supervisor verifies its coherence before
closure.

All file-capable agents inspect task-relevant Project Canonical Skills by direct,
project-relative reads at `.aether/skills/<skill-name>/SKILL.md`. The convention follows
the project's repository visibility and does not require a loader or a duplicate skill
registry. Aether package-owned canonical procedures are loaded only through the existing
package/native profile skill mechanism. Skills provide reusable procedure only and remain
subordinate to owner instruction, the constitution, `DESIGN.md`, stage specifications,
Objective Contracts, and these repository rules; no skill grants authority.

For contract progress, changes, blockers and observation failures in this project, read
the Project Canonical Skill `.aether/skills/aether-observe/SKILL.md`. It selects the
compact observation view first and expands only the relevant authoritative evidence;
it does not replace independent review or final contract-result acceptance.

Adoption of the contract/execution procedures was tracked in
[issue #317](https://github.com/DarkArty07/Aether-Agents/issues/317) and
[the execution guide](docs/guides/execution.md#contractexecution-procedure-adoption);
its open-ended observation requirement was closed at owner direction without claiming
organic PASS. Do not claim the behavior is qualified merely because resources are
installed, or recreate the retired synthetic campaign. This does not alter testing
authority for other objectives. Morfeo's final result reception uses
`contract-result-review` before owner-objective acceptance; see `DESIGN.md` section 10.1.
Execution closeout remains Supervisor-owned. Keep evidence attributed and distinguish
resource tests from observed agent behavior.

## External research sources

Research checkouts stay outside this repository. They are evidence sources, not vendored dependencies or project sources of truth.

- **GitHub Spec Kit**
  - Upstream: `https://github.com/github/spec-kit.git`
  - Local checkout used for the historical comparison: `<private-spec-kit-checkout>`
  - Baseline inspected for the current design research: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`
  - This is historical research evidence, not a claim about the currently installed or checked-out tree. Refresh and identify the source before relying on current Spec Kit behavior.

- **Hermes Agent**
  - Upstream: `https://github.com/NousResearch/hermes-agent.git`
  - **Selected public release evidence:** release `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution `hermes-agent` `0.20.4`, Python `>=3.11,<3.14`. This remains the reference baseline for upstream-compatible behavior and historical qualification evidence.
  - **Executable release source:** maintained fork `https://github.com/DarkArty07/aether-hermes.git` branch `aether-main`. Each release binds the exact accepted commit, source-tree digest, artifact closure and provenance through release-lock source mode `maintained_fork` (emitted as `schema_version` 5, readable as schema 4); the retired `transitional_fork` mode is refused for new preparation.
  - A locally loaded editable Hermes tree, its path, and its observed revision are runtime evidence only. They are not a distributable dependency or manually maintained durable documentation.
  - Resolve the source actually loaded, its version, and its revision at investigation time before making a runtime claim. Research checkouts and live local state remain read-only evidence during canonical design work; an authorized release candidate must start from the exact accepted maintained-fork commit and the exact accepted Aether revision, and must never copy private editable state or replay `.patch` files onto an active runtime.
  - The live profile under `home/` is evidence of what is initialized, not documentation of intent; its contents are never adopted merely by being present.

> **Verify a claim in code before an accepted decision rests on it.** Documentation states intent; the registry states what is actually exposed. R5 claimed role containment was structural in both directions until the tool gating was read, which showed card creation is available to every worker. Where a decision depends on something being impossible, read the gate — not the guide.

> **Resolve the source before reading it.** More than one checkout of a dependency can exist on a machine, and the one under the obvious path may not be the one the runtime loads. Recording an exact revision proves *what* you read — it does not prove you read the right thing. For an installed package, resolve the actual load path first (editable install pointers, `pip show`, the interpreter's own resolution) and record the version alongside the revision. A capability claim made against the wrong tree is worse than no claim, because it carries a citation.

Before relying on current Spec Kit behavior, refresh the external checkout and record the exact inspected revision. Decisions derived from that research must be captured in Aether's own accepted design artifacts.

Local changes require proportionate verification. Commit, publication, release and other remote effects require separate explicit authority.
