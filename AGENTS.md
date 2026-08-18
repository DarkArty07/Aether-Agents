# Aether Agents repository

This repository contains the versioned policy and reproducible configuration for Aether Agents.

`DESIGN.md` is the canonical conceptual design for the current redesign. It defines the intended roles, authority boundaries and fixed high-level product decisions. Technology choices not explicitly fixed there remain undecided and must not be inferred or implemented without Christopher's direction.

The live Hermes profile is local state under `home/` and must not be committed. Keep credentials, sessions, databases, memories and other runtime state private.

The current runtime may remain a single Hermes profile while the redesign is being specified. Do not treat the conceptual multi-agent design as authorization to create profiles, workers, schedulers, coordination runtimes or other implementation mechanisms before their technical design is explicitly decided.

Only Morfeo currently has a proper agent name. The other two agent identities are role descriptions only: supervision and implementation. The implementation role is intended to be replicable in parallel instances. Hermes Framework and GitHub Spec Kit are selected foundations. A2A is only the preferred communication candidate until its fit and scope are evaluated; no integration mechanism should be inferred from framework availability.

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

This principle belongs in Aether's future constitution. Until that artifact exists, it lives here.

## External research sources

Research checkouts stay outside this repository. They are evidence sources, not vendored dependencies or project sources of truth.

- **GitHub Spec Kit**
  - Upstream: `https://github.com/github/spec-kit.git`
  - Local checkout: `/home/darkarty/Desktop/agentes/aether-research/spec-kit`
  - Baseline inspected for the current design research: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`
  - Verified 2026-08-17: exactly one Spec Kit tree exists on this machine, its HEAD equals `origin/main`, and Spec Kit is not installed as a package — so unlike Hermes there is no second authoritative tree to confuse it with.

- **Hermes Agent**
  - Upstream: `https://github.com/NousResearch/hermes-agent.git`
  - **The source Aether runs:** `home/.venv-hermes/src/hermes-agent` — version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`. The profile installs Hermes as an editable package pointing here.
  - **Not this one:** `/home/darkarty/.hermes/hermes-agent` is a different, older checkout (0.19.1). It is not what the Aether profile loads. Reading it produced a false finding once already.
  - Read; never modify either tree as part of Aether design work.
  - The live profile under `home/` is runtime evidence about what is initialized. It is not documentation of intent, and its contents are not adopted by being present.

> **Verify a claim in code before an accepted decision rests on it.** Documentation states intent; the registry states what is actually exposed. R5 claimed role containment was structural in both directions until the tool gating was read, which showed card creation is available to every worker. Where a decision depends on something being impossible, read the gate — not the guide.

> **Resolve the source before reading it.** More than one checkout of a dependency can exist on a machine, and the one under the obvious path may not be the one the runtime loads. Recording an exact revision proves *what* you read — it does not prove you read the right thing. For an installed package, resolve the actual load path first (editable install pointers, `pip show`, the interpreter's own resolution) and record the version alongside the revision. A capability claim made against the wrong tree is worse than no claim, because it carries a citation.

Before relying on current Spec Kit behavior, refresh the external checkout and record the exact inspected revision. Decisions derived from that research must be captured in Aether's own accepted design artifacts.

Local changes require proportionate verification. Commit, publication, release and other remote effects require separate explicit authority.
