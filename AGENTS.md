# Aether Agents repository

This repository contains Aether's public product source, versioned policy, canonical specifications, and reproducible configuration. The current build target is the Aether 1.0 contract in `specs/001-aether-v1-productization/`; a design decision or local candidate is not evidence that a package, release candidate, public service, or stable release exists.

`DESIGN.md` is the canonical conceptual design for the current redesign. It defines the intended roles, authority boundaries and fixed high-level product decisions. Technology choices not explicitly fixed there remain undecided and must not be inferred or implemented without Christopher's direction.

Live Hermes profiles and other runtime state under `home/` are local evidence only and must not be committed. Keep credentials, sessions, databases, memories, logs, boards, repositories, owner identifiers, machine paths, and private provider/model/router bindings out of public artifacts.

The accepted product has three roles: Morfeo, supervision, and implementation. Implementation is replicable in parallel instances. The accepted design and A1 contract still grant no authority by themselves to create or activate profiles, start workers or services, invoke models, acquire credentials, publish, deploy, cut over an installation, or perform another protected external effect.

**Current stabilization authority (PD-71 through PD-74, 2026-08-26):** ordinary local/reversible work is governed by scope, worktrees, Git, tests, review and rollback rather than role micro-permissions. The pre-tool hook is restricted to high-confidence secrets/credentials, credential acquisition/widening, unauthorized remote/external mutation, and clearly destructive irreversible effects. Morfeo recovery is rollback-first and bounded; Implementer owns local technical judgement; Supervisor may make small integration repairs. Feature expansion and nonessential Hermes changes remain frozen until the rolling E2E reliability gate passes.

Only Morfeo has a proper agent name; supervision and implementation remain role descriptions. Hermes Agent and GitHub Spec Kit are selected foundations. Aether reuses native Hermes profiles, Projects, boards, worktrees, review, and lifecycle where they qualify. A2A remains available but unused under R6; framework availability never authorizes an integration mechanism.

The selected public Hermes baseline is `NousResearch/hermes-agent` release `v2026.8.18`: annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, dereferenced commit `e624e9fde561e1add9388384012b295fde669ade`, distribution `hermes-agent` `0.20.4`, Python `>=3.11,<3.14`. A1 starts in `transitional_fork` mode under PD-65 only for indispensable qualified fixes; no new Aether capability may depend on a downstream-only core change, and each patch retires when an exact released upstream artifact passes its behavior gate.

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

## External research sources

Research checkouts stay outside this repository. They are evidence sources, not vendored dependencies or project sources of truth.

- **GitHub Spec Kit**
  - Upstream: `https://github.com/github/spec-kit.git`
  - Local checkout used for the historical comparison: `<private-spec-kit-checkout>`
  - Baseline inspected for the current design research: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`
  - Verified 2026-08-17: exactly one Spec Kit tree exists on this machine, its HEAD equals `origin/main`, and Spec Kit is not installed as a package — so unlike Hermes there is no second authoritative tree to confuse it with.

- **Hermes Agent**
  - Upstream: `https://github.com/NousResearch/hermes-agent.git`
  - **Selected public release evidence:** release `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution `hermes-agent` `0.20.4`, Python `>=3.11,<3.14`.
  - **The source the private Aether installation currently runs:** `home/.venv-hermes/src/hermes-agent` — version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`. It is historical/runtime evidence for that installation, not the selected public release source or a distributable dependency.
  - **Not this one:** `<legacy-hermes-checkout>` is a different, older checkout (0.19.1). It is not what the Aether profile loads. Reading it produced a false finding once already.
  - Research checkouts and the loaded private tree are read-only evidence during canonical design work. A separately authorized downstream implementation must use an isolated candidate based on the exact selected public release and must not copy private editable state.
  - The live profile under `home/` is runtime evidence about what is initialized. It is not documentation of intent, and its contents are not adopted by being present.

> **Verify a claim in code before an accepted decision rests on it.** Documentation states intent; the registry states what is actually exposed. R5 claimed role containment was structural in both directions until the tool gating was read, which showed card creation is available to every worker. Where a decision depends on something being impossible, read the gate — not the guide.

> **Resolve the source before reading it.** More than one checkout of a dependency can exist on a machine, and the one under the obvious path may not be the one the runtime loads. Recording an exact revision proves *what* you read — it does not prove you read the right thing. For an installed package, resolve the actual load path first (editable install pointers, `pip show`, the interpreter's own resolution) and record the version alongside the revision. A capability claim made against the wrong tree is worse than no claim, because it carries a citation.

Before relying on current Spec Kit behavior, refresh the external checkout and record the exact inspected revision. Decisions derived from that research must be captured in Aether's own accepted design artifacts.

Local changes require proportionate verification. Commit, publication, release and other remote effects require separate explicit authority.
