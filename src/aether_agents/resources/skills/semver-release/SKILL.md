---
name: semver-release
description: Classify SemVer impact and release action safely.
version: 0.1.0
author: Christopher, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [semver, release, prerelease, stable, compatibility]
    related_skills: []
---

# SemVer and Release Skill

Use this procedure to make the three independent release conclusions for one authorized
objective: compatibility impact, release action, and publication channel. It owns the
classification and release-gate procedure, not GitHub closeout mechanics. It is
subordinate to the current owner instruction, Objective Contract, project policy, and
repository rules; this skill cannot grant authority.

## When to Use

- Use when an objective changes a public compatibility contract or release-visible
  behavior and a release disposition must be reported.
- Use when deciding `release_impact`, `release_action`, and `release_channel` together
  without conflating their meanings.
- Do not use as a substitute for acceptance, PR/check/merge, issue reconciliation, or
  branch cleanup; use the Git/GitHub closeout procedure for those mechanics.
- Do not use when project policy or public compatibility evidence leaves a material
  ambiguity; return that question through Morfeo instead of guessing.

## Prerequisites

- The objective's acceptance evidence and the project's compatibility and release policy
  are available in the checkout.
- The current version source, changelog rules, default branch, and tag convention are
  identified from repository files.
- Evidence and public resource references use project-relative paths; machine-specific
  locations remain outside the skill.
- Any publication credentials are already provisioned and remain outside artifacts.
- The owner gate for special stable publication is known; no skill bypasses it.

## How to Run

Inspect source, tests, version metadata, changelog, and release policy with the
`read_file`, `search_files`, and `terminal` tools. Use the repository's existing release
workflow only after its standing policy and the contract authorize the selected action.
Do not create a second release registry or workflow engine.

## Quick Reference

- `terminal(command="git diff --stat")`
- `terminal(command="git diff --check")`
- `terminal(command="git describe --tags --always")`
- `terminal(command="git show-ref --tags")`
- `terminal(command="git status --short --branch")`

## Procedure

1. Read the objective acceptance, public compatibility contract, current version source,
   changelog, release policy, and release workflow. Identify the exact evidence that
   makes the classification deterministic.
2. Classify compatibility impact independently as exactly one of `none`, `patch`,
   `minor`, or `major`. Use `major` for incompatible public changes, `minor` for
   compatible public additions, `patch` for compatible fixes, and `none` when no release
   impact is evidenced. Return a material ambiguity through Morfeo.
3. Choose release action independently as exactly one of `defer`, `prepare`, or `publish`.
   Follow standing project policy; a merge does not imply a release, and `publish` never
   follows from impact alone.
4. Choose channel independently as exactly one of `none`, `prerelease`, or `stable`.
   A prerelease channel is not a compatibility-impact class. Keep a release candidate
   such as `v1.0.0-rc.1` coherent with its package representation such as `1.0.0rc1`.
5. If preparing a version or changelog, update only the files authorized by the objective.
   Check that package metadata, version source, changelog, tag expectation, and release
   metadata agree. Do not rewrite an existing tag.
6. For a prerelease, require the project's RC policy and mark the GitHub/package result as
   prerelease. For stable, require the exact verified commit at the protected default
   branch, exact version/ref agreement, all qualification gates, and any explicit owner
   gate. Otherwise use `defer` or record the missing gate.
7. Run the focused release-decision and version-coherence tests plus the repository's
   documented quality gates. Inspect the actual workflow-owned logic rather than proving
   only that a desired string appears in documentation.
8. Report all three conclusions, evidence, omitted effects, and rollback implications.
   Keep a correct `defer`/`none` result visible; do not represent unqualified behavior as
   a release.

## Pitfalls

- `prerelease` is a channel, never `release_impact`.
- A version bump, a prepared artifact, or a passing local test does not authorize tag,
  GitHub Release, package publication, deployment, or installation cutover.
- Do not infer compatibility from file count, commit size, or a dependency's version.
- Do not accept malformed, mismatched, non-default-branch, or rewritten tag candidates.
- Do not weaken a special stable-release gate because a generic project policy permits
  routine releases.

## Verification

- Assert the three fields are present and each belongs to its independent allowed set.
- Compare version source, package metadata, changelog, expected tag/ref, and release
  metadata byte-for-byte or through the repository's existing deterministic checks.
- Exercise stable and RC cases, including malformed/mismatched/default-branch refusals,
  without making an external publication.
- Record test commands, observed results, selected conclusions, and every remaining gate.
