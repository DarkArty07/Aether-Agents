---
name: canonical-skill-governance
description: Govern portable canonical skills without granting authority.
version: 0.1.0
author: Christopher, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, governance, portability, discovery, promotion]
    related_skills: []
---

# Canonical Skill Governance Skill

Use this procedure to classify, discover, maintain, and promote reusable skill
procedures. Skills own method only: they do not own product intent, project truth,
execution status, constitutional principles, or role authority. This skill cannot grant authority
and does not create a loader, router, or duplicate registry.

## When to Use

- Use when deciding whether a procedure is Aether Canonical, Project Canonical, or a
  Learned Profile Skill.
- Use when discovering task-relevant project procedures or reviewing a promotion from
  private adaptive learning into versioned source.
- Use when maintaining a canonical skill's triggers, pitfalls, verification, or scope.
- Do not use to invent owner intent, alter acceptance, grant permissions, or replace
  repository guidance and normative artifacts.

## Prerequisites

- Read the current owner instruction, constitution, conceptual design, applicable stage
  specification, Objective Contract, repository rules, and root `AGENTS.md`.
- Inspect the actual project worktree and current source before making a portability claim.
- Use only project-relative paths in public skill text; keep credentials, runtime state,
  identities, providers, models, repositories, and machine paths out of it.
- An independent reviewer and normal repository change path are available for promotion.

## How to Run

Use `read_file` and `search_files` to inspect guidance and skill files. Use `write_file`
or `patch` for the scoped repository change, and `terminal` for tests and Git evidence.
Do not add a skill index, registry, generic loader, daemon, or framework patch.

## Quick Reference

- `search_files(pattern="SKILL.md", target="files", path=".aether/skills")`
- `read_file(path=".aether/skills/<skill-name>/SKILL.md")`
- `read_file(path="AGENTS.md")`
- `terminal(command="git diff --check")`
- `terminal(command="git status --short")`

## Procedure

1. Identify the class and owner. Aether Canonical Skills are public, versioned, and
   package-owned at `src/aether_agents/resources/skills/<skill-name>/SKILL.md`.
   Project Canonical Skills are tracked, versioned, and portable under
   `.aether/skills/<skill-name>/SKILL.md`. Learned Profile Skills remain private,
   local, adaptive, non-canonical state and never auto-promote.
2. Discover project procedures through root `AGENTS.md` and direct project-relative
   reads of `.aether/skills/<skill-name>/SKILL.md`. Discover Aether procedures through
   the package/native profile mechanism already provided by the product. Load only what
   the task needs; do not maintain a stale per-project list.
3. Resolve precedence for compatible procedures: current owner instruction,
   constitution/design/stage specifications/Objective Contract and repository rules
   govern first; a more-specific Project Canonical Skill outranks an Aether Canonical
   Skill, and both outrank a Learned Profile Skill. No skill can override authority.
4. Maintain a canonical skill by preserving its name and location, tightening its
   trigger, keeping procedure non-overlapping, documenting pitfalls, and adding an
   executable verification path. Change the owning repository file, not private copies.
5. Promote a learned procedure only after sanitization, generalization, focused
   verification, independent review, commit, and pull request. Remove private text,
   identities, machine paths, runtime state, providers, models, repository details,
   credentials, and assumptions that do not travel with the procedure.
6. When a change invalidates project operating guidance, update the root `AGENTS.md` in
   the same authorized change. Preserve brownfield guidance; do not make `aether init`
   invent generic content. Supervisor verifies coherence before closure.
7. Report the class, source path, precedence used, verification result, privacy review,
   review/commit/PR evidence, and any unresolved material question.

## Pitfalls

- A skill's presence, package inclusion, or profile loading does not make it product
  truth or grant authority.
- Learned skills are not canonical merely because they worked once; promotion is never
  an automatic copy.
- Do not copy a private skill wholesale into public source or expose a local profile
  directory recursively.
- Do not add a routing/index skill when direct discovery and the catalog are sufficient.
- Do not overwrite an existing brownfield `AGENTS.md` with generic initialization text.

## Verification

- Validate frontmatter, unique name, version, concise trigger, platform claim, body,
  linked resources, project-relative paths, privacy, and procedural-only scope.
- Prove a disposable project can read a named `.aether/skills/<skill-name>/SKILL.md`
  through the root `AGENTS.md` convention without a new loader.
- Run focused tests, `terminal(command="git diff --check")`, and the applicable docs,
  package, and public-artifact checks. Record observed output and residual risk.
