# Contributor Documentation

> **Status:** STRUCTURE CURRENT; root contributor workflow reconciled by ODR-0001

This area will explain how to change Aether Agents while preserving product intent, architecture boundaries, and repository quality.

## Planned contributor set

| Document | Purpose |
|---|---|
| `DEVELOPMENT_SETUP.md` | Local development environment and dependencies |
| `WORKFLOW.md` | Branches, commits, pull requests, reviews, and releases |
| `TESTING.md` | Test layers, focused gates, full-suite expectations, and evidence |
| `DOCUMENTATION.md` | Documentation taxonomy, status vocabulary, style, and link checks |
| `ARCHITECTURE_CHANGES.md` | Design and decision requirements for structural changes |
| `ADDING_OR_CHANGING_A_DAIMON.md` | Role, authority, SOUL, config, toolset, and evaluation workflow |
| `RUNTIME_ADAPTER_DEVELOPMENT.md` | Replacement-runtime adapter, isolation, lifecycle, cleanup, and compatibility verification |
| `RELEASES.md` | Versioning, metadata synchronization, tags, and closeout evidence |

## Active workflow

The repository uses direct `feature → main` integration. `main` is the latest integrated, tested state; annotated tags and GitHub Releases represent official published versions. ODR-0001 governs standing GitHub automation authority, branch disposition, next-version preflight and release reflection.

## Contributor rules

1. Read product scope and principles before proposing architecture.
2. Do not mix unrelated dirty work into a contribution.
3. Use exact, reproducible verification evidence.
4. Keep live configs, secrets, runtime state, and generated artifacts out of commits.
5. Update documentation when changing a public or operational contract.
6. Preserve historical evidence while marking superseded active direction.
