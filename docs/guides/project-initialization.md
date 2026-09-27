# Project initialization

`aether init` makes an **existing Git repository root** an Aether Project. It is implemented and intentionally narrow.

## Preconditions

- Run at the repository root (or pass that root as `PATH`); an unborn Git root (`git init`) is accepted, while a plain directory and a subdirectory of a repository are refused with `git init` guidance.
- If an exact-path native Hermes Project already exists, `aether init` reuses it. If none exists, `aether init` creates and verifies exactly one native Hermes Project through the selected runtime CLI.
- If several native Projects have that exact path, provide the desired ID with `--hermes-project ID`.

The command never archives or modifies existing native Projects, and it never chooses by display name, slug, current directory, or an approximate path.

```bash
# Discovery only: no marker or registry write.
aether init --dry-run

# Initialize the existing repository root.
aether init [PATH] [--name NAME] [--forge local|github] [--hermes-project ID]
```

## Result

On success, initialization:

1. writes or validates `.aether/project.toml` against the canonical project schema;
2. registers the portable project UUID against the repository path and exact native Hermes Project ID in local Aether state; and
3. ensures `.aether/project.toml` and finalized `.aether/objective-contracts/` paths are trackable while `.aether/drafts/` stays ignored.

It appends the canonical ignore-policy block only when necessary. It does not overwrite an invalid existing marker, silently merge a copied identity, or modify unrelated ignore rules. A moved repository can re-register a stale mapping only after identity validation; two live repositories with the same portable project identity are refused.

## Operating guidance and project skills

`aether init` deliberately does not create or overwrite root `AGENTS.md`. Morfeo
establishes missing project guidance only after inspecting repository reality and
confirming the project's constitution. In a brownfield repository, existing guidance is
preserved and reconciled rather than replaced with generic text. The role whose
authorized change invalidates operating instructions updates `AGENTS.md` in that same
change, and Supervisor verifies its coherence before closure.

Agents discover task-relevant Project Canonical Skills through that root guidance and a
direct read of `.aether/skills/<skill-name>/SKILL.md`. These files are tracked and
portable with the project; initialization keeps the `.aether/skills/` convention
trackable while leaving drafts and other local `.aether/` state ignored. It does not
create a skill registry, loader, or stale list of skill names. Skills provide procedure
only and cannot grant authority.

## Methodology after initialization

Initialization binds identity; Morfeo establishes working guidance from the actual
project after inspecting its existing instructions and confirming the constitution.
It does not copy Aether-Agents, invent product decisions, or create a complete empty tree.
The `objective-contract-design` project-adoption/predesign entry owns this procedure.

Keep root `AGENTS.md` concise: governing documents and their locations, relevant project
procedures, actual setup/run/test/distribution guidance and preservation boundaries.
Mark unknowns instead of inventing commands. Distribution instructions do not authorize
publication. Preserve other harness instructions and use accessible project-relative
references; a private Hermes memory or skill is not a portable source of obligations.

| Information | Project location / boundary |
| --- | --- |
| Product code, tests, specs, technical plans, research, docs and deliverables | Outside `.aether`, using the project's structure; `specs/` and `docs/` are examples, not migration orders. |
| Portable Aether identity, finalized contracts and project procedures | `.aether/project.toml`, `.aether/objective-contracts/`, `.aether/skills/`; retain their existing versioned roles. |
| Draft contracts and Objective Plans | Local `.aether/drafts/` and `.aether/plans/`; ignore by default under the accepted privacy policy. |
| Unresolved exploration that merits continuity | One local `.aether/observations/<topic>.md`, not a requirement, board or runtime-observation projection. |
| Discretionary project scratch | Owned `.aether/tmp/<work-scope>/`, not scattered through the root; preserve necessary evidence before cleanup. |

An observation distinguishes concern, facts/sources, hypotheses, questions, decisions and
continuity. Resolve it by answering, transferring a decision to its owning artifact, or
justifying an objective; only then retire an eligible owned note after preserving what
is still needed. No observation, plan or new Project Canonical Skill is mandatory for
a trivial task. Do not publish or discard the whole `.aether` tree indiscriminately.
Tool-managed runtime state, worktrees, caches and required external research locations
retain their rules. This convention grants no retrospective migration or broad cleanup.

Other file-capable harnesses can follow this map without reproducing Aether's runtime.
If a step genuinely needs an Aether capability, state that dependency rather than
inventing an equivalent. See [expected behaviors](expected-behavior.md) and the
[authority map](../authority.md).

## Greenfield limit

`aether init` supports empty directories initialized by the owner with `git init`, but it does **not** run `git init` itself. Run `git init` in an empty or brownfield directory first, then run `aether init`. This keeps Git creation under the owner's explicit control.

For the parser surface, see [CLI reference](../reference/cli.md). For the identity's role in handoff, see [Objective Contracts](objective-contracts.md).
