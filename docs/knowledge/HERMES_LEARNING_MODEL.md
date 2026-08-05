# Hermes Agent Learning Model Used by Aether

> **Status:** CURRENT PRODUCT GOVERNANCE + VERIFIED HERMES MECHANICS
> **Mechanics verified:** 2026-07-26 against Hermes Agent 0.19.0
> **Aether configuration:** `home/config.yaml.template`
> **Governing decision:** `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`

## Purpose

This document records the learning, memory, and skill capabilities Aether already receives from `hermes-agent`. It prevents Aether from rebuilding a parallel learning framework and identifies the narrower governance layer the product still needs.

## Conclusion

Hermes Agent already provides the core self-improvement loop Aether needs:

- persistent user-profile and agent memory through `USER.md` and `MEMORY.md`;
- automatic background memory and skill review;
- autonomous creation and patching of skills through `skill_manage`;
- explicit skill distillation through `/learn`;
- progressive skill loading;
- skill usage and provenance tracking;
- periodic skill lifecycle maintenance through Curator.

Aether should reuse these mechanisms. Its own responsibility is to define authority, scope, project isolation, write ownership, and quality rules around them.

## Tracked Aether configuration

The active Aether Hermes home is the repository's `home/` directory. Relevant configuration:

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 4000
  user_char_limit: 3000

skills:
  external_dirs:
    - /home/arty/Escritorio/agentes/aether/home/skills
  template_vars: true
  inline_shell: false
  guard_agent_created: false

curator:
  enabled: true
  interval_hours: 168
  min_idle_hours: 2
  stale_after_days: 30
  archive_after_days: 90
  backup:
    enabled: true
    keep: 5
  consolidate: false
```

The v0.22.0 tracked template uses Hermes-native memory directly. It declares no external semantic-memory provider or service dependency.

## Built-in memory

Hermes maintains two bounded stores:

- **USER.md / user profile:** identity, communication preferences, expectations, workflow habits, and other facts about the user.
- **MEMORY.md / agent memory:** stable environment facts, conventions, tool behavior, durable lessons, and compact facts the agent should always have available.

The installed system prompt explicitly instructs Hermes to:

- prioritize memories that prevent future user correction;
- save stable facts rather than temporary work state;
- avoid PR numbers, commit hashes, phase completion, transient TODOs, and other quickly stale information;
- write declarative facts rather than imperative self-instructions;
- put procedures and workflows in skills instead of memory.

Aether raises the built-in limits above Hermes defaults to 4,000 characters for memory and 3,000 for the user profile.

### Hermes as profile custodian

Hermes' role is not merely to read these files. As the primary user-facing agent, Hermes must continuously manage the user model:

- detect explicit preferences and recurring corrections;
- distinguish durable patterns from temporary instructions;
- normalize and deduplicate profile entries;
- correct or remove stale preferences;
- keep personal preferences separate from environment facts;
- pass only relevant context to Daimons;
- prevent specialist assumptions from becoming global user truth;
- preserve current explicit intent as the highest authority.

This custodianship is a core part of Hermes' product value.

## Approved memory topology

Aether's approved target memory topology uses Hermes-native `USER.md` and `MEMORY.md` without Honcho or another external semantic memory provider.

Honcho was retired from tracked configuration, setup, distribution, and active operational documentation in v0.22.0 because it caused operational problems and added a second memory service and authority surface. Historical decision and release evidence remains preserved.

Hermes is the global user-profile custodian. It detects durable preferences, separates them from one-off requests, organizes and deduplicates the profile, corrects stale entries, and decides which relevant user context should accompany delegated work.

Daimons may report possible preferences or durable observations, but they do not independently own or redefine the global user model. Current explicit user instructions always override stored memory.

## Automatic skill creation and improvement

### Foreground instruction

The Hermes system prompt tells the active agent to save a reusable skill after:

- a complex task using five or more tool calls;
- a difficult error whose working solution was discovered;
- a non-trivial reusable workflow.

It also instructs the agent to patch an outdated, incomplete, or incorrect skill immediately rather than waiting for the user to request maintenance.

This behavior is model-mediated: the instruction is present, but the model may or may not act correctly in the foreground.

### Background review

Hermes separately tracks tool iterations. The installed default `skills.creation_nudge_interval` is 10 because Aether does not override it.

When accumulated tool iterations reach that threshold and `skill_manage` is available, Hermes:

1. completes and delivers the user's response;
2. resets the skill counter;
3. starts a background review agent;
4. gives it the conversation and a restricted memory/skills toolset;
5. asks it to update the skill library actively.

The background review is instructed to prefer, in order:

1. patching a skill used in the session;
2. patching an existing class-level umbrella skill;
3. adding a `references/`, `templates/`, or `scripts/` support file;
4. creating a new class-level umbrella skill only when no suitable skill exists.

Signals include:

- user corrections to style, format, workflow, or approach;
- non-trivial techniques, fixes, workarounds, and debugging paths;
- a loaded skill proving stale, incomplete, or wrong.

The reviewer is explicitly told not to create narrow one-session skills, store transient failures as durable prohibitions, or preserve one-off task narratives.

The review is best-effort and model-mediated, not a deterministic guarantee. Failures are swallowed so they never block the user's task.

### Explicit `/learn`

Hermes also provides `/learn`. It turns a directory, URL, pasted notes, a described procedure, or the workflow just completed into a standards-guided `SKILL.md` using the live agent's normal tools.

This is the user-directed path when a procedure should definitely be captured rather than left to the background review heuristic.

## Skill storage and loading

Skills are procedural memory: reusable instructions for how to perform a class of task.

Hermes uses progressive disclosure:

1. a compact skill index is visible in the prompt;
2. `skill_view` loads the main `SKILL.md` only when needed;
3. references, templates, scripts, and assets load individually on demand.

Aether stores shared skills in `home/skills/`, which is the common skill source for Hermes and the Daimon profiles.

Existing writable skills in configured external directories can be patched in place by `skill_manage`. Therefore, filesystem location is not itself a write-protection boundary.

## Evidence that Aether already uses the loop

The 2026-07-26 `home/skills/.usage.json` inspection recorded:

- **137** tracked skill records;
- **42** records with agent-created or curator-managed provenance;
- all 137 currently marked `active`.

Examples then marked `created_by: agent` included:

- `aether-framework-quality-governance`;
- `api-contract-delivery`;
- `asclepio-project`;
- `autonomous-pilot-governance`;
- `execution-monitoring`;
- `external-model-relay`;
- the since-retired Graphify integration skill.

The usage ledger also records views, uses, patch counts, timestamps, pin state, and lifecycle state. This is direct evidence that skill creation and iterative patching are active parts of Aether's current workflow.

## Curator

Curator is a separate background skill-lifecycle mechanism. It is not the primary mechanism that learns from each completed task.

Aether's current Curator policy is:

- enabled;
- checked every 168 hours;
- allowed to run after at least two idle hours;
- skills become stale after 30 unused days;
- skills become archive candidates after 90 unused days;
- five backups are retained;
- LLM consolidation is disabled.

Because `consolidate: false`, a normal Curator run performs only deterministic inactivity lifecycle work. It does not currently run the auxiliary-model umbrella-building and overlap-consolidation pass.

Curator archives rather than permanently auto-deleting. Backups and restoration exist so maintenance remains recoverable.

## Current write-governance observation

`skills.guard_agent_created` is currently `false`. In Hermes this setting controls the content scanner for agent-created skill writes; it does not disable skill creation itself.

Therefore, the current Aether configuration favors autonomous skill writing without that optional content-scanning approval layer. Whether this should remain the desired product policy is a later design and safety decision, not established by this research document.

## What Aether should not rebuild

Aether should not create a parallel implementation for:

- detecting every reusable workflow;
- writing skills from scratch outside `skill_manage`;
- maintaining another global preference database;
- building another semantic user-memory provider;
- inventing another skill usage ledger;
- creating a second skill curator;
- loading procedural knowledge through a competing format.

Duplicating those mechanisms would create conflicting sources of truth and undermine the decision to build Aether on Hermes Agent.

## Aether-specific governance still required

Hermes provides learning mechanics, but Aether still needs product rules for:

### 1. Knowledge authority

- User preferences and personal facts belong in Hermes-managed `USER.md`.
- Stable environment facts and compact operational lessons belong in Hermes-managed `MEMORY.md`.
- Reusable procedures belong in Hermes skills.
- Project vision, scope, requirements, architecture decisions, and current milestone authority belong in version-controlled project documentation and `.aether` continuity—not only in memory or skills.
- Source, tests, artifacts, and executed evidence remain authoritative for actual behavior.

### 2. Scope and promotion

A project-specific solution must not become a global skill unless it is generalized into a reusable class of work with explicit applicability and non-applicability conditions.

The default should be to patch an existing class-level skill or add a reference file rather than create a new narrow skill.

### 3. Current-intent precedence

Current explicit user instructions override:

- USER/MEMORY entries;
- existing skills;
- learned workflow preferences;
- historical project patterns.

### 4. Write ownership

Aether must eventually decide:

- which profiles may create or patch shared skills;
- whether specialist Daimons write directly or propose changes through an owner;
- which skills should be pinned;
- whether project repositories may carry project-local skills;
- how changes are reviewed, versioned, reverted, and tested;
- whether the optional skill-content guard should be enabled.

### 5. Quality and contamination control

A skill update is not automatically correct merely because Hermes created it. Skill quality requires:

- a reusable class-level trigger;
- steps grounded in successful execution;
- pitfalls and verification;
- avoidance of transient prohibitions;
- no conflict with current product doctrine;
- no leakage of project secrets or private data;
- correction or removal when evidence changes.

## Product Discovery Phase 6 result

Phase 6 approved the following:

1. Hermes Agent's native learning loop is Aether's canonical learning mechanism.
2. Honcho is excluded from the target product.
3. Hermes is the central custodian of the user's profile, preferences, and global memory.
4. Project authority remains in version-controlled documents and `.aether`, not in global memory.
5. Daimons may report observations but do not independently own the global user model.
6. Shared skills should remain reusable and user-neutral; current user preferences normally belong in `USER.md`.

Remaining design work includes defining shared-skill write governance, deciding whether private per-user skills are needed, and governing how MCP-derived observations become evidence or durable learning. The Honcho source/config retirement is complete in the v0.22.0 candidate.
