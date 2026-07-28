# ODR-0001: Keep `main` integrated and automate the GitHub release lifecycle

- **Status:** APPROVED
- **Date:** 2026-07-28
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** The mixed legacy assumption that merge to `main` is equivalent to release publication
- **Superseded by:** None

## Context

Between 2026-07-18 and 2026-07-28, Aether accumulated more than 130 commits across the v0.19 coordination branch, a stacked canonical-documentation branch, and the v0.20 self-improvement branch while `main` remained at v0.18.2. The work was committed and often verified, but integration repeatedly remained outside each roadmap closeout.

The repository contained contradictory guidance:

- the current branching model said `feature/{name} -> main`; and
- a stale section still said `feature -> dev -> main (release)`.

Release, merge, activation, deployment and publication were then frequently grouped as one protected boundary. A v0.19.x closeout explicitly allowed the next topic to start while PR #113 remained draft. This made an unmerged feature branch the de facto integration branch and allowed later candidates to stack on it.

Christopher's actual preference is SemVer, atomic commits, strong evidence and autonomous technical execution. It is not a preference for keeping `main` stale. He now grants standing authority for routine GitHub lifecycle operations when deterministic gates pass.

## Decision

### 1. `main` is the integration branch, not the release object

`main` represents the latest integrated, tested repository state. It may contain default-off, unreleased or not-yet-activated capabilities.

An official release is represented separately by:

1. a SemVer value in the supported version metadata;
2. an annotated `vX.Y.Z` tag;
3. a GitHub Release for that tag; and
4. release evidence that corresponds to the exact tagged `main` commit.

Merge to `main` does not imply runtime activation, deployment, migration or public product availability.

### 2. Features integrate directly to `main`

Every normal feature branch starts from the current `origin/main` and returns to `main` through a pull request. The obsolete `dev` branching model is removed.

Stacked PRs are forbidden by default. A temporary stacked PR requires a versioned decision that names:

- the parent PR;
- why direct integration is impossible;
- the exact merge order;
- the retargeting plan; and
- the deadline for removing the stack.

### 3. A predecessor needs a terminal branch disposition

Before a new SemVer candidate begins, the previous candidate must be one of:

- **MERGED** — integrated into `main`;
- **ABANDONED** — intentionally discarded with rationale; or
- **SUPERSEDED** — replaced by a named candidate that preserves or explicitly rejects its scope.

`CLOSED`, `VIABLE`, `IMPLEMENTED`, `VERIFIED`, `DEFAULT-OFF` or `UNPUBLISHED` are not branch dispositions by themselves.

A roadmap may finish its technical question without publishing a release, but a new SemVer candidate must not be built on an unmerged predecessor.

### 4. Agents have standing GitHub authority

For Aether Agents, authorized agents may perform these actions without requesting per-action confirmation:

- create atomic commits;
- push branches;
- create, update, retarget and mark PRs ready;
- enable auto-merge or merge after required gates pass;
- delete merged branches;
- create annotated SemVer tags on the exact integrated `main` commit;
- create or reconcile GitHub Releases;
- update and close linked issues and milestones after merge.

The `authorization` block inside a version candidate such as `docs/releases/v0.20.0/CYCLE.yaml` remains a fail-closed statement of that candidate's current gate state. It does not revoke this standing repository authority; it means the candidate has not yet satisfied the conditions that permit agents to exercise it. Once the candidate's independent review and deterministic release gates pass, no additional product-owner confirmation is required for the GitHub operations in this section.

This standing authority is valid only when:

- the user-approved or project-approved scope is unchanged;
- the exact committed candidate passes required tests and checks in a clean checkout;
- the PR targets `main` unless a valid stacked-PR decision exists;
- CI is green, or an explicitly documented equivalent deterministic gate exists;
- no unresolved P0/P1, security, trust, data-loss or release blocker remains;
- the operation does not require force-push, history rewriting or bypassing required checks.

### 5. GitHub authority does not grant operational authority

The standing authority does not include:

- runtime activation or restart;
- deployment or production publication outside GitHub Releases;
- data migration or deletion;
- credential, account or secret changes;
- spending;
- destructive history rewriting;
- accepting known material regressions.

Those remain governed by their own product or operational policies.

### 6. Release reflection is automatic

A pushed `vX.Y.Z` tag triggers the repository release workflow. The workflow must fail closed unless:

- the tag is valid SemVer;
- the tag points to the exact current `origin/main` commit;
- the package version equals `X.Y.Z`;
- current release documentation contains the same version;
- the committed tree passes its release checks.

After validation, the workflow builds artifacts and creates or reconciles the GitHub Release. A tag without a corresponding GitHub Release is an incomplete boundary and must be repaired automatically or reported as a blocker.

### 7. Branch health is checked before the next version

Before creating a new SemVer branch, agents run:

```bash
python scripts/check_release_governance.py preflight-next-version --version X.Y.Z
```

The preflight requires:

- current branch `main`;
- clean working tree;
- local `main` equal to `origin/main`;
- no open earlier SemVer candidate PR targeting `main`;
- no unresolved stacked version PR;
- the next version to be greater than the latest published tag.

Failure blocks creation of the next version branch.

## Rationale

SemVer and automatic GitHub integration solve different problems. SemVer names accepted public capability boundaries. `main` keeps the repository integrated and reviewable. Conflating them made each experimental gate postpone integration and produced large, difficult-to-audit branch stacks.

Standing GitHub authority removes repetitive approval friction while retaining deterministic safety. It matches Christopher's preferred role as product owner: he owns product direction and meaningful consequences, while agents own routine technical execution and repository hygiene.

## Alternatives considered

### Keep `main` equal to the latest public release

Rejected. It turns long-running feature branches into hidden integration branches, makes CI and documentation drift, and increases merge and attribution risk.

### Auto-merge every green PR without semantic gates

Rejected. Green CI does not prove scope fidelity, product correctness or release readiness.

### Require confirmation for every push, PR, merge and tag

Rejected. It recreates coordination burden for routine reversible repository operations and directly caused integration backlog.

### Use a permanent `dev` branch

Rejected. The repository explicitly adopted direct feature-to-main integration in May 2026. Reintroducing `dev` would add another long-lived divergence point without solving release identity.

## Consequences

### Positive

- `main` remains current and meaningful.
- Tags and GitHub Releases accurately represent official versions.
- Default-off work can integrate without being activated or published as a release.
- Agents can close routine GitHub loops without approval fatigue.
- A new SemVer candidate cannot silently stack on an unresolved predecessor.
- Release state becomes mechanically checkable.

### Negative

- Agents must maintain clean candidate and release evidence discipline.
- Some previously valid stacked-PR workflows become invalid.
- Existing PRs #113 and #120 require reconciliation under this policy.
- An incorrect tag will fail the automated release workflow rather than creating a partial release.

## Validation or review gate

Implementation is accepted when:

1. `AGENTS.md` contains one non-contradictory feature-to-main model;
2. no active policy says `dev -> main (release)`;
3. PR governance rejects an ordinary PR whose base is not `main`;
4. next-version preflight rejects a dirty, stale or non-main starting state;
5. release validation rejects a tag that differs from package version or does not point to `origin/main`;
6. a valid tag workflow creates or reconciles its GitHub Release;
7. automated GitHub authority remains separate from deployment, activation, migration, credentials and spending;
8. tests cover the policy parser and validation rules.

## Implementation authorization

Approval of this record authorizes local implementation, commits, branch push, PR creation and routine GitHub settings needed to enable auto-merge and automatic branch deletion.

It also establishes standing future authority for the GitHub operations in Decision §4 when their gates pass.

It does not authorize merging the current v0.20.0 correction candidate until its independent review and required checks are complete. It does not authorize runtime activation, restart, deployment, migration, credential changes or spending.

## References

- Repository policy: `../../AGENTS.md`
- Release governance checker: `../../scripts/check_release_governance.py`
- PR governance workflow: `../../.github/workflows/release-governance.yml`
- Automated release workflow: `../../.github/workflows/release.yml`
- Historical v0.19.x closeout: `../releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md`
- Product-owner authority: `PDR-0004-product-owner-authority-and-bounded-autonomy.md`
- SemVer self-improvement policy: `PDR-0009-semver-self-improvement-cycle.md`
