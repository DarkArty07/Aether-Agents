---
name: contract-result-review
description: Use when Morfeo receives a completed contract result.
version: 0.1.0
author: Christopher, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [acceptance, contracts, evidence, reception]
    related_skills: []
---

# Contract Result Review

Receive the completed result against the owner's intent, not just its delivery status.
Supervisor retains implementation review, integration and execution closeout. This skill
provides method only and cannot grant authority, change acceptance or add a board state.

## When to Use

- Use when Morfeo receives a Supervisor terminal result, before reporting owner-objective
  acceptance, including a follow-up asking whether the delivered work is really complete.
- For bounded direct self-review, use the same acceptance reasoning without claiming an
  independent reviewer or manufacturing a contract/card that the objective did not need.
- Not for contract extraction, Supervisor's incoming contract receipt, or claimed
  same-card implementation review. Do not apply another role's lifecycle verdict here.

## Prerequisites

- Current owner instruction, finalized contract/version where applicable, acceptance,
  testing standard, scope/preservation and authority for the delivered outcome.
- Durable delivery evidence and an accessible final artifact with an identifiable revision.
- Already provisioned file, terminal or artifact-inspection access. An unavailable source
  is a limit to report, not permission to acquire credentials, call providers or deploy.

## How to Run

Use `kanban_show` for execution evidence, `read_file` and `search_files` for requirements
and delivered content, and `terminal` for exact Git/PR identity and authorized checks.
Inspect generated outputs where they are the deliverable; source presence alone is not
proof of the rendered or running result. Use only the existing permitted tool surface.

## Procedure

1. **Read intent before the handoff.** Read current owner instruction and the owning
   contract, not a paraphrase from the delivery. Identify every material criterion and
   preservation/authority obligation. Mark examples as examples. If the contract itself
   loses the owner's intent, report that conflict; do not certify against a weaker target.
2. **Bind the exact delivery.** Read durable board state and identify project, contract
   version, exact revision, PR/artifact and evidence producer. A test log from an earlier
   commit is not final-revision proof. Reuse it only with inspected change-impact evidence
   that explains applicability; otherwise rerun the relevant check or mark it unverified.
3. **Inspect the delivered result.** Find the actual artifact/location for every material
   criterion. Follow the user-facing journey or observable output, not just a file list.
   Green unrelated tests, all cards marked done and a confident narrative cannot fill a
   missing requirement. Inspect content fidelity as well as build/test correctness.
4. **Check proportionately.** Choose checks from the agreed testing standard and the
   unresolved risk: not a fixed sample quota and not an automatic full-suite rerun. Reuse
   traceable Supervisor/Implementer evidence where appropriate; directly test decisive
   outcomes and doubts with authorized tools. A check that cannot be exercised is
   unverified, or blocking if material. Never invent a passing output to fill the table.
5. **Record a compact reception.** Use the objective's existing evidence location and
   ordinary reversible workflow, not a new registry, mandatory schema or copy of the
   contract. Use project-relative evidence references. Cover every material criterion,
   with these facts (table layout is optional):

   | Criterion | Actual artifact/location and revision | Check, evidence producer | Result/limit |
   | --- | --- | --- | --- |
   | Existing criterion reference | Project-relative location in final output | Direct or reused evidence, with revision | Supported, mismatch or unverified |

   Label **directly verified by Morfeo**, **reused pipeline evidence**, and **unverified**
   distinctly. A retained upstream test result is not an independent Morfeo rerun. Record
   authorized omissions and who authorized them. Keep private identities, paths, runtime
   state, credentials and raw logs out of public evidence. Reference existing evidence
   rather than duplicating it; update verification applicability if reception adds a commit.
6. **Decide and report.** Accept only when material outcomes have sufficient evidence
   and no unresolved material mismatch. Summarize what was delivered, direct versus reused
   verification and remaining limits. Distinguish execution complete, objective accepted
   and publication/deployment authorized; do not invent a completion percentage. A clean
   result ends reception without another card or review loop. For a material discrepancy,
   provide criterion, expected/observed result and reproducible evidence to Supervisor via
   supported continuation/rework. Do not issue a same-card review verdict from an unclaimed
   or finished task, write the board DB, or take over product implementation. If the native
   path is unavailable, report the real blocker rather than inventing a parallel lifecycle.

## Pitfalls

- **No acceptance waiver:** neither this skill nor a new contract version can turn an
  unapproved exception into owner authority. Intent changes belong to the owner.
- Checking a hash proves byte identity, not correctness, completeness or usability.
- A local preview is not production. A PR is not a deployment; a merge is not a release.
- Reviewing your own direct work is self-review, not independent pipeline evidence.
- A procedure on disk is not a behavioral guarantee. No extra agent, hook, loader or
  acceptance engine is implied. Do not repeatedly review a correct result for ceremony.

## Verification

Before the owner-facing conclusion, verify that the reception references the exact
artifact, covers every material criterion, attributes reused evidence, records checks
actually performed and makes any unverified requirement visible. Confirm supported
routing of material discrepancies, or finish honestly when acceptance is supported.

Metadata, package-byte and instruction-presence tests verify resources, not agent
obedience. Qualify behavior separately through authorized real reception: observe missing
requirements despite green status, stale evidence, inaccessible material checks, justified
reuse and a correct delivery accepted without redundant full-suite execution. Do not
claim those cases were exercised merely because this list exists.
