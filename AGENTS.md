# Aether Agents repository

This repository contains Aether's public product source, versioned policy, canonical specifications, and reproducible configuration. The current build target is the Aether 1.0 contract in `specs/001-aether-v1-productization/`; a design decision or local candidate is not evidence that a package, release candidate, public service, or stable release exists.

`DESIGN.md` is the canonical conceptual design for the current redesign. It defines the intended roles, authority boundaries and fixed high-level product decisions. Technology choices not explicitly fixed there remain undecided and must not be inferred or implemented without an owner decision.

Live Hermes profiles and other runtime state under `home/` are local evidence only and must not be committed. Keep credentials, sessions, databases, memories, logs, boards, repositories, owner identifiers, machine paths, and private provider/model/router bindings out of public artifacts. For the complete reader-facing placement and conflict-resolution map across all artifact classes, see [`docs/authority.md`](docs/authority.md).

The accepted product has three roles: Morfeo, supervision, and implementation. Implementation is replicable in parallel instances. The accepted design and A1 contract still grant no authority by themselves to create or activate profiles, start workers or services, invoke models, acquire credentials, publish, deploy, cut over an installation, or perform another protected external effect.

**Current stabilization authority (PD-71 through PD-74, 2026-08-26):** ordinary local/reversible work is governed by scope, worktrees, Git, tests, review and rollback rather than role micro-permissions. The pre-tool hook is restricted to high-confidence secrets/credentials, credential acquisition/widening, unauthorized remote/external mutation, and clearly destructive irreversible effects, plus one contract-directed integrity guard: a `kanban_create` whose `title`/`body` ends in a transport truncation sentinel is refused before persistence (`specs/007-session-residual-stability/spec.md` §SR-227), which is not a role or permission decision. Morfeo recovery is rollback-first and bounded; Implementer owns local technical judgement; Supervisor may make small integration repairs. Feature expansion and nonessential Hermes changes remain frozen until the rolling E2E reliability gate passes, except for explicitly owner-authorized bounded objectives. The current Telegram Monitor exception is owned by `specs/telegram-monitor/spec.md`; it permits only that objective's documentation, implementation, verification and reversible local activation through provisioned access. It does not waive reliability/release gates or authorize unrelated runtime changes.

Only Morfeo has a proper agent name; supervision and implementation remain role descriptions. Hermes Agent and GitHub Spec Kit are selected foundations. Aether reuses native Hermes profiles, Projects, boards, worktrees, review, and lifecycle where they qualify. A2A remains available but unused under R6; framework availability never authorizes an integration mechanism.

Executable Hermes source is Aether's maintained fork `DarkArty07/aether-hermes` branch `aether-main`, bound by release-lock `schema_version` 4 source mode `maintained_fork` through repository, exact commit, source-tree digest, artifacts and provenance, and installed through `aether update`. The earlier fixed public baseline `NousResearch/hermes-agent` `v2026.8.18` — annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution `hermes-agent` `0.20.4`, Python `>=3.11,<3.14` — remains a reference baseline for upstream-compatible behavior and historical evidence, not the deployment input. `.patch` files and HLP records are audit/reconstruction evidence and are never replayed onto the active runtime; the retired `transitional_fork` mode is refused for new preparation. Hermes keeps its own distribution identity (`hermes-agent`). No new Aether capability may depend on a downstream-only core change, and each accepted fork change retires when an exact released upstream artifact passes its behavior gate.

The RC6 bounded corrective objective is `oc_b5926701207812e8@v1`, designed in `specs/001-aether-v1-productization/plan-rc6.md`: finish mixed-version lifecycle compatibility, observer startup/native-query reliability and portable launcher guidance, then qualify one local candidate `1.0.0rc6` / `1.0.0-rc.6` / `v1.0.0-rc.6`. Its conclusions are `release_impact=patch` / `release_action=prepare` / `release_channel=prerelease`; the annotated tag remains local-only, never pushed. This is not stable `1.0.0`, PyPI publication or WSL2 qualification; #261 stays open. #485 is the owning objective issue, with #488 and #490 included and related launcher/service issues reconciled only against actual evidence. The failed rc5 contract `oc_a7a3cff05e82c148@v1` remains non-accepted history; operational recovery does not retroactively accept it. Exact frozen old readers/writers must be tested in isolation before live effects, and coherent rc5 is the only live fallback for this objective. Executable Hermes stays at maintained-fork merge `aed6591a69f453a1867b73628603e7b53ba40ffc` (`#450`+`#461`) for this objective's own lane, and that commit remains the installed runtime pin. The separately authorized #494 source phase advanced the maintained fork's `aether-main` to `58f8c37a49b341f25b8fdd6310542fe932031b8d` with reviewed source, a portable artifact and reconciled evidence only; its live adoption is a deferred successor, not a runtime change. The separately authorized source repair for issue #433 then advanced the same branch to `621047dc1c10cceb2825013cc8bb611b4d0e8de1` (reviewed auxiliary Responses reasoning-usage preservation, portable artifact and reconciled evidence only); its live adoption is likewise a deferred successor and the installed runtime pin named above is unchanged. Existing rc.2 through rc.5 tags and activation records remain immutable; the published-but-rejected rc1 (`oc_3397f9f05d780f8e@v1`) must not be activated. Automatic deployments to the existing Aether GitHub Pages site caused by reviewed green merges required by this objective remain authorized; no manual Pages dispatch, other target or unrelated deployment is authorized.

Current owner-authorized local maintenance for #497/#495 is a two-candidate managed update. RC7 is the compatibility bridge with RC6-identical Morfeo SOUL and canonical contract skills; this `1.0.0rc8` source revision restores the #495 planning guidance and the #497 updater repair. For #487, the owner's accepted option B gives Hermes ownership of the complete main gateway unit; Aether verifies only its required service invariants, as reconciled in A1. Source or a local tag alone cannot establish qualification, active runtime selection or improved agent behavior: require reviewed Git evidence, exact-version isolation and a verified managed cutover. No tag is pushed or published. These maintenance candidates do not accept the outstanding RC6 objective, qualify stable release or WSL2, or authorize unrelated runtime changes.

The owner-authorized Morfeo MCP objective (#515) continues in this `1.0.0rc10` candidate. RC9 remains the schema-4 reader that can install a schema-5 target. RC10 emits schema 5 with `hermes.extras: [mcp]` and adds `aether mcp morfeo serve`. The executable Hermes pin remains `aed6591a69f453a1867b73628603e7b53ba40ffc`. No Hermes fork change, tag push, or stable release is authorized.


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

For objective planning and cross-session continuation, see
[`docs/guides/objective-plans.md`](docs/guides/objective-plans.md) and the
`objective-contract-design` canonical procedure's planning entry. Keep one local
`.aether/plans/<objective-slug>.md` when a meaningful route or continuity is needed;
do not select by recency, duplicate canonical obligations, or add plan ceremony to
simple bounded work. Plans remain local/ignored unless publication is explicitly
decided. A session or contract boundary does not reset failed approaches or the
reasoning needed to justify continuation. Source instructions do not prove live adoption.

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
  - **Executable release source:** maintained fork `https://github.com/DarkArty07/aether-hermes.git` branch `aether-main`. Each release binds the exact accepted commit, source-tree digest, artifact closure and provenance through release-lock `schema_version` 4 source mode `maintained_fork`; the retired `transitional_fork` mode is refused for new preparation.
  - A locally loaded editable Hermes tree, its path, and its observed revision are runtime evidence only. They are not a distributable dependency or manually maintained durable documentation.
  - Resolve the source actually loaded, its version, and its revision at investigation time before making a runtime claim. Research checkouts and live local state remain read-only evidence during canonical design work; an authorized release candidate must start from the exact accepted maintained-fork commit and the exact accepted Aether revision, and must never copy private editable state or replay `.patch` files onto an active runtime.
  - The live profile under `home/` is evidence of what is initialized, not documentation of intent; its contents are never adopted merely by being present.

> **Verify a claim in code before an accepted decision rests on it.** Documentation states intent; the registry states what is actually exposed. R5 claimed role containment was structural in both directions until the tool gating was read, which showed card creation is available to every worker. Where a decision depends on something being impossible, read the gate — not the guide.

> **Resolve the source before reading it.** More than one checkout of a dependency can exist on a machine, and the one under the obvious path may not be the one the runtime loads. Recording an exact revision proves *what* you read — it does not prove you read the right thing. For an installed package, resolve the actual load path first (editable install pointers, `pip show`, the interpreter's own resolution) and record the version alongside the revision. A capability claim made against the wrong tree is worse than no claim, because it carries a citation.

Before relying on current Spec Kit behavior, refresh the external checkout and record the exact inspected revision. Decisions derived from that research must be captured in Aether's own accepted design artifacts.

Local changes require proportionate verification. Commit, publication, release and other remote effects require separate explicit authority.
