# Aether Agents repository

This repository contains the versioned policy and reproducible configuration for Aether Agents.

`DESIGN.md` is the canonical conceptual design for the current redesign. It defines the intended roles, authority boundaries and fixed high-level product decisions. Technology choices not explicitly fixed there remain undecided and must not be inferred or implemented without Christopher's direction.

The live Hermes profile is local state under `home/` and must not be committed. Keep credentials, sessions, databases, memories and other runtime state private.

The current runtime may remain a single Hermes profile while the redesign is being specified. Do not treat the conceptual multi-agent design as authorization to create profiles, workers, schedulers, coordination runtimes or other implementation mechanisms before their technical design is explicitly decided.

Only Morfeo currently has a proper agent name. The other two agent identities are role descriptions only: supervision and implementation. The implementation role is intended to be replicable in parallel instances. Hermes Framework and GitHub Spec Kit are selected foundations. A2A is only the preferred communication candidate until its fit and scope are evaluated; no integration mechanism should be inferred from framework availability.

## External research sources

Research checkouts stay outside this repository. They are evidence sources, not vendored dependencies or project sources of truth.

- **GitHub Spec Kit**
  - Upstream: `https://github.com/github/spec-kit.git`
  - Local checkout: `/home/darkarty/Desktop/agentes/aether-research/spec-kit`
  - Baseline inspected for the current design research: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`

Before relying on current Spec Kit behavior, refresh the external checkout and record the exact inspected revision. Decisions derived from that research must be captured in Aether's own accepted design artifacts.

Local changes require proportionate verification. Commit, publication, release and other remote effects require separate explicit authority.
