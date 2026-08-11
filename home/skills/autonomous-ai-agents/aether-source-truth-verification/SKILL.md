---
name: aether-source-truth-verification
description: "Use when verifying current Aether roles or runtime truth."
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [aether, source-verification, daimons, runtime, provenance]
    related_skills: [hermes-agent]
---

# Aether Source-Truth Verification

## Overview

Use this skill to answer factual questions about Aether identities, Daimons, participant policy, runtime availability, architecture, releases, or operating paths. The goal is not merely to find a matching sentence: it is to identify which source currently has authority and separate an approved target role from an operationally qualified capability.

A familiar name in the prompt, memory, a profile, or release history is a lead—not sufficient proof of current runtime truth.

Detailed source-layer examples and the Hefesto case that motivated this procedure live in `references/source-authority-map.md`. The authority-versus-confirmation correction for Aether MCP work lives in `references/authority-vs-confirmation.md`. Revalidate every example against the current tree before using it as evidence.

## When to Use

Load this skill when the user asks:

- who or what an Aether component, Daimon, archetype, service, or tool is;
- where an Aether role or policy is documented;
- whether a participant is retained, allowed, disabled, forbidden, callable, qualified, or active;
- whether a historical profile or protocol is still authoritative;
- why Hermes made an Aether-specific factual claim;
- to reconcile conflicting prompt, documentation, repository, runtime, or session-history claims.

Do not use it for generic Hermes Agent documentation, unrelated repositories, or broad product design where no current-truth claim is at issue.

## The Source-Layer Model

Classify evidence before synthesizing it.

| Layer | What it can establish | Typical evidence |
|---|---|---|
| Current user authority | Product meaning, current permission, explicit correction | Current conversation |
| Active prompt policy | Hermes routing and behavior currently loaded | Active `home/SOUL.md`, exact prompt version |
| Canonical product decision | Approved role, lifecycle, architecture, target policy | Current PDR/ADR and canonical product docs |
| Release status and gates | What is implemented, qualified, pending, or blocked now | Current `STATUS.yaml`, roadmap, operating policy |
| Runtime evidence | What the installed system actually exposes or executes | Current MCP/status responses and deterministic probes |
| Profile definition | Identity and role contract, if still admitted | Profile `SOUL.md`, config/template, digests |
| Historical evidence | How the system used to work | README snapshots, changelog, old releases, retired source |
| User preference/history | How this user wants work routed or reported | Durable memory and session history |

No lower layer overrides a higher authority. A source can remain useful for identity while being obsolete for invocation mechanics.

## Workflow

### 1. Resolve the exact project root

Verify the repository root before searching. Do not infer it from the active agent name, an ambient home, or memory alone.

**Completion:** the exact root is known and every subsequent path is relative to that single canonical checkout.

### 2. Read the project authority banner first

Inspect the nearest `AGENTS.md` or equivalent project context before interpreting matches. Look for active-version boundaries, the current branch, retired paths, and statements that older sections are history only.

**Completion:** current authority, canonical checkout, and explicitly retired mechanisms are identified.

### 3. Search all mentions, then narrow by authority

Search the exact term case-insensitively across the verified root. Record the total match count, but do not treat frequency as authority. Narrow to:

1. active prompt;
2. governing decision;
3. architecture/role contract;
4. current release status and roadmap;
5. live runtime evidence when operational availability is claimed.

Use README, profile files, changelog, tests, and old releases only after their status is classified.

**Completion:** every claim planned for the answer has at least one current authoritative source or is explicitly labeled historical/preference-only.

### 4. Build the role-versus-availability matrix

For every participant or capability, resolve these independently:

- **identity:** what the role is called;
- **target function:** its distinct contribution;
- **lifecycle:** retained, conditional, proposed, or retired;
- **participant policy:** required, allowed, disabled, or forbidden;
- **implementation state:** profile/design present or absent;
- **qualification state:** whether the current release gate passed;
- **runtime availability:** whether the admitted path can call it now;
- **effect authority:** what it may modify or activate in this Task.

Never collapse these dimensions into a single “available” label.

**Completion:** an `allowed` or `retained` role is not called operational unless qualification and runtime evidence also support that claim.

### 5. Detect stale operational instructions

A profile can accurately describe a specialist's identity while still naming a retired invocation path. Compare its communication/runtime section against the current project authority. Preserve useful role evidence, but reject stale instructions such as retired MCPs, managers, aliases, or fallback paths.

**Completion:** no historical mechanism is presented as current merely because it appears inside a still-present profile.

### 6. Attribute user-specific policy separately

When a claim comes from persistent preference or prior conversation—such as a preferred fallback owner—label it as user policy, not canonical product architecture. If the original direct source is accessible, inspect it before using session history.

**Completion:** the answer distinguishes repository truth, runtime truth, and user preference instead of blending them.

### 7. Answer with line-level provenance

Lead with the corrected current truth. Cite relative path and line range for the decisive sources. When a broad search returns many historical matches, report the total and summarize the current authoritative subset; provide an exhaustive dump only if requested.

If an earlier answer mixed layers or overstated availability, say exactly which part was valid, which part was unsupported, and what the corrected formulation is.

**Completion:** the user can reproduce the conclusion from the named sources and can see what remains pending or unknown.

## Required Distinctions

### Retained is not operational

`retained` means the archetype remains in the target design. It does not prove that its profile is bound, its model route is qualified, its dispatch gate passed, or Orca can execute it now.

### Allowed is not dispatched

`allowed` permits selection when all other gates are satisfied. It does not grant provider, model, budget, mutation, attempt, or dispatch authority.

### Explicit authority is not a confirmation prompt

Do not translate “explicit provider/model/effect/budget authority” into “ask the user again.” First inspect current user intent, approved project policy, participant policy, admitted configuration, and the Task contract; then use the MCP's read-only inspection and validation surfaces. If existing authority admits the operation, proceed without burdening the user with routine mechanics.

Ask only when a genuinely uncovered material boundary remains: protected or irreversible effects, credentials, spending, publication, cross-project impact, or a typed denial/`UNKNOWN` that authoritative inspection cannot resolve. Separate release-level qualification gates from per-Task authority; a historical or pending release milestone is not automatically a permanent confirmation ritual. See `references/authority-vs-confirmation.md`.

### Present is not authoritative

A profile, source directory, README row, or test fixture can remain physically present as historical evidence after its runtime path is retired.

### Role truth is not protocol truth

A profile may still correctly say “Production Builder” while incorrectly saying “invoked through Olympus.” Treat each section according to current authority rather than accepting or rejecting the whole file wholesale.

### Memory is not product documentation

Memory can establish a durable user preference. It cannot prove current repository contents, release state, or runtime availability.

## Common Pitfalls

1. **Answering from the injected prompt alone.** The prompt is authoritative for Hermes behavior, but current product/runtime claims still require project and status evidence.
2. **Reporting the first matching file.** Search results mix active policy, stale profiles, changelog, tests, and marketing copy.
3. **Equating role approval with runtime readiness.** Always inspect qualification and operational gates.
4. **Treating a profile as atomic truth.** Its identity section may be current while its invocation section is retired.
5. **Hiding provenance after a correction.** State whether the original claim came from prompt policy, project docs, runtime evidence, memory, or inference.
6. **Using session history before a direct source.** Search the repository, URL, file, runtime, or issue first when the user identified one.
7. **Dumping hundreds of matches without synthesis.** Give the total, classify the evidence, and cite the decisive current sources.
8. **Silently preserving an overstatement.** Replace “is available” with the exact matrix state: e.g. “retained and allowed, but qualification is pending.”
9. **Turning contract authority into user ceremony.** Do not ask permission merely to use Aether MCP/Orca. Inspect and validate existing authority first; escalate only the smallest genuinely uncovered material boundary.

## Verification Checklist

- [ ] Exact Aether project root and single canonical checkout verified
- [ ] Current project authority banner inspected
- [ ] Exact term searched across the relevant tree
- [ ] Active prompt version identified when prompt policy matters
- [ ] Governing decision and canonical architecture checked
- [ ] Current release status and gate state checked
- [ ] Runtime evidence checked for operational claims
- [ ] Identity, lifecycle, policy, qualification, availability, and authority separated
- [ ] Historical and retired references labeled rather than silently used
- [ ] User preference/history attributed separately
- [ ] Decisive claims include reproducible path and line references
- [ ] Any earlier overstatement explicitly corrected
