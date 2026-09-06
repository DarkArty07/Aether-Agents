# Design authoring checkpoint for #312

Status: partial, not independently qualified, not packaged/activated, and not closed.
This file records observed work and limitations; the owning spec/plan/quickstart define
acceptance. It is not a PASS receipt or an Objective Contract.

## Authored by Morfeo

- Three standalone candidate canonical skills in the package resource tree.
- Focused additions to Morfeo, Supervisor and Implementer SOUL resources.
- R2/R3/R7 obligations and the Objective Contracts planning-ownership clarification.
- Objective spec, technical plan and seven-case runnable qualification design.
- ROADMAP states reopened rather than falsely claiming the new refinement is complete.

No Python runtime, Objective Contract schema, configured toolset, provider/model,
concurrency, active profile or historical finalized contract was changed.

## Actual checks

- Three skill files: frontmatter, required headings, description bounds, version,
  platform declarations and basic portability checks passed. These are structural
  checks, not proof of intellectual behavior.
- `scripts/check_documentation.py`: passed after staging all authored files.
- `git diff --cached --check`: passed after correcting one Markdown trailing-space line.
- First combined documentation/Objective Contract run in the lightweight source
  environment: 39 passed, 5 failed because `hermes_cli` was absent. No package installed.
- Repeated with the provisioned Hermes interpreter, candidate Aether source and
  disposable home/state: **40 passed, 4 failed**. The four native-board failures trace
  to the inherited `HERMES_DELEGATED_CHILD_CONTEXT=1` marker in the parent TUI process,
  which causes the existing delegated-child mutation guard to refuse temporary boards.
- Exact failure added to [#310](https://github.com/DarkArty07/Aether-Agents/issues/310#issuecomment-5555304526).
  No identity marker was suppressed, no guard was patched and no live board was used.

## Review and remaining work

Two read-only auxiliary reviews were requested: role/procedure coherence and technical
qualification feasibility. At this checkpoint their final verdicts have not yet been
incorporated. They do not implement product changes and do not replace the downstream
independent Supervisor qualification.

The existing lab was found to copy SOUL from its imported package, not the supplied
profile-root, and not to load the new skills. Its generic success predicate also cannot
represent expected contract rejection. The plan therefore specifies finite test-only
support with explicit baseline/candidate resource selection, expected-defect oracles
and actual native run overlap; no new agent tool, production evaluator or general
runtime schema change. That test support and Python resource registration are not yet
implemented or claimed to exist.

Qualification is blocked by false parent lineage (#310). The shared runtime has
pre-existing concurrent changes; no safe objective-owned infrastructure rollback was
available, and this objective does not absorb that runtime repair. Recover the genuine
parent context through the authorized runtime recovery path before retrying the native
board tests or attempting pipeline handoff. Do not use an env-marker workaround as proof.

No Objective Contract was finalized, no pipeline root was dispatched, no PR/merge,
release or profile activation was performed. The candidate must stay isolated and the
issue open until review, implementation, Q1–Q7, activation and normal closeout have actual
evidence. Preserve unrelated source branches/worktrees, ignored project material and
private runtime state; the new design worktree is intentional unfinished residue.
