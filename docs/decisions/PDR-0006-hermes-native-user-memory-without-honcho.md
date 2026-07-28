# PDR-0006: Hermes-native user memory without Honcho

- **Status:** APPROVED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** Any product assumption that Honcho is part of Aether's target memory architecture
- **Superseded by:** None

## Context

Aether is built on Hermes Agent specifically to reuse its mature agent infrastructure rather than rebuild foundational capabilities. Inspection of the installed Hermes Agent 0.19.0 source confirmed that Hermes already provides:

- persistent `USER.md` and `MEMORY.md` stores;
- automatic background memory review;
- automatic skill creation and patching through `skill_manage`;
- explicit skill distillation through `/learn`;
- skill usage and provenance tracking;
- Curator lifecycle maintenance;
- session search for historical transcript recall.

Aether had also configured Honcho as an external memory provider and documented it as part of the memory topology. The owner reports that Honcho caused operational problems and has decided that Aether will not use it.

The product requires one clear owner for the user's profile and preferences. Because Hermes is the primary user-facing agent and the interpreter of product intent, user modeling and global memory management are part of Hermes' essential value.

## Decision

### 1. Hermes Agent is the canonical learning framework

Aether will reuse Hermes Agent's native mechanisms for:

- user profile persistence;
- stable memory;
- automatic memory review;
- automatic skill creation and improvement;
- explicit `/learn` skill distillation;
- skill usage tracking;
- Curator lifecycle maintenance;
- session-history recall.

Aether must not create a competing general memory engine, skill format, skill curator, or automatic learning loop unless a verified Hermes limitation cannot be addressed through extension or configuration.

### 2. Honcho is excluded from the target product

Honcho is not part of Aether's approved target memory architecture.

Aether will not depend on Honcho for:

- user profiling;
- preference storage;
- cross-session continuity;
- project state;
- semantic authority;
- product installation or normal operation.

Historical Honcho documentation and setup artifacts may remain temporarily for migration, archaeology, or cleanup planning, but they must be marked as legacy or retired and must not be presented as the current recommended path.

The current `home/config.yaml` still declares `memory.provider: honcho`. This is a documented configuration discrepancy. Approval of this decision does not itself authorize changing runtime configuration; that change requires a later bounded implementation task.

### 3. Hermes owns the global user profile and memory

Hermes is the sole conceptual custodian of the user's global profile and preferences.

Hermes is responsible for:

- detecting durable user preferences from explicit statements and repeated corrections;
- distinguishing stable preferences from one-off requests;
- organizing preferences into a compact, coherent user profile;
- maintaining stable environment and operating facts separately from personal preferences;
- correcting, deduplicating, superseding, or removing stale memory;
- ensuring current explicit user instructions override stored preferences;
- deciding what user context is relevant to pass to a Daimon;
- preventing specialist observations from becoming global user truths without validation;
- keeping sensitive credentials and secrets out of plain-text memory.

This responsibility is part of Hermes' primary-agent value, not a secondary utility.

### 4. Daimons do not own the global user model

Daimons may observe a possible preference, correction, or durable lesson while performing specialist work. They may report that observation to Hermes or include it in structured evidence.

They must not independently redefine the global user profile, create conflicting user models, or make specialist-local assumptions globally authoritative.

Hermes decides whether the observation belongs in:

- `USER.md` as a user preference or profile fact;
- `MEMORY.md` as a stable environment or operating fact;
- a reusable skill as procedural knowledge;
- project documentation or `.aether` as project-specific continuity;
- nowhere, when it is temporary, uncertain, sensitive, or not reusable.

The exact runtime enforcement mechanism remains a later design decision.

### 5. Knowledge placement

The approved conceptual placement is:

| Knowledge | Canonical location |
|---|---|
| User identity, communication style, preferences, recurring corrections | Hermes-managed `USER.md` |
| Stable environment facts, durable conventions, tool quirks | Hermes-managed `MEMORY.md` |
| Reusable procedures and verified workflows | Hermes skills via `skill_manage` and `/learn` |
| Project vision, scope, requirements, durable decisions, architecture | Version-controlled project documentation |
| Current project phase, active task, blockers, hot continuity | `.aether` project continuity |
| Historical conversation details | Hermes session history and `session_search` |
| Actual software behavior | Source, tests, artifacts, runtime evidence |

Project-specific decisions must not become global user preferences. User-specific preferences must not become universal technical truth.

### 6. Shared skill governance

Hermes may continue using its native automatic skill loop.

However, user-specific preferences should normally remain in `USER.md` rather than being embedded into shared, user-neutral skills. A shared skill may describe how to consult and honor the active user profile, but should not hard-code one user's preference as a universal workflow rule.

Whether Aether later supports private per-user skills in addition to shared product skills remains open.

## Rationale

Hermes already performs the difficult foundational work of memory and procedural learning. Reusing it keeps Aether focused on its differentiation: specialist coordination, quality, product continuity, user alignment, and evidence.

Removing Honcho reduces installation burden, service dependencies, operational failure modes, and ambiguity over which memory system is authoritative.

Centralizing the user model in Hermes matches the product-owner interaction model. Hermes is the agent that speaks with the user, interprets intent, detects corrections, and decides what context specialists need. Allowing every Daimon to maintain an independent global user model would create contradiction and preference drift.

## Alternatives considered

### Keep Honcho as an optional advanced provider

- **Benefits:** Semantic retrieval and deeper external user modeling remain available.
- **Costs:** Additional service topology, installation failures, operational burden, duplicate memory authority, and a path the owner no longer trusts.
- **Decision:** Rejected for the approved product direction.

### Build an Aether-native memory subsystem

- **Benefits:** Full control over data model and multi-agent semantics.
- **Costs:** Rebuilds Hermes capabilities, creates competing sources of truth, and expands scope without demonstrated need.
- **Decision:** Rejected.

### Let each Daimon maintain its own user profile

- **Benefits:** Specialist-local personalization.
- **Costs:** Conflicting profiles, duplicated facts, specialist bias, privacy complexity, and inconsistent behavior.
- **Decision:** Rejected for global user memory.

### Store all user preferences directly in shared skills

- **Benefits:** Task-specific behavior can start already adapted.
- **Costs:** Contaminates shared skills with one user's preferences and creates poor behavior for other users.
- **Decision:** Rejected as the default. Shared skills should consult Hermes-managed user context instead.

## Consequences

### Positive

- One canonical user-profile owner.
- Fewer external services and installation steps.
- No dependency on Honcho availability or data model.
- Better alignment between current user intent, profile, delegation context, and product decisions.
- Aether remains an extension of Hermes rather than a competing agent framework.

### Negative

- Hermes' bounded built-in memory may be less semantically powerful than an external provider.
- Profile quality depends on Hermes correctly identifying and curating durable preferences.
- Multi-user isolation and portability still require explicit product design.
- Existing Honcho configuration, scripts, docs, and dependencies need a later retirement plan.

### Risks

- Hermes may overlearn one-off preferences or preserve stale corrections.
- Automatic skill review may still embed user-specific behavior into shared skills unless governed.
- Daimons may receive insufficient user context if Hermes delegates poorly.
- Removing Honcho without verifying the native-memory path could expose hidden dependencies.

## Validation or review gate

Later implementation and evaluation must demonstrate:

1. Aether starts and operates without Honcho;
2. the current config no longer selects Honcho;
3. user preferences persist across sessions through Hermes-native memory;
4. Hermes corrects and removes stale preferences;
5. current explicit instructions override stored profile data;
6. Daimons receive only relevant user context;
7. project-specific facts do not contaminate the global user profile;
8. shared skills do not hard-code one user's preferences as universal rules;
9. historical Honcho docs and commands are clearly retired or removed;
10. no feature silently depends on Honcho for normal operation.

## Implementation authorization

Approval of this record authorizes documentation alignment and preparation of a later Honcho-retirement plan. It does not authorize configuration changes, deletion of Honcho data, submodule removal, dependency removal, runtime restart, migration, deployment, or release activity.

## References

- Hermes learning model: `docs/knowledge/HERMES_LEARNING_MODEL.md`
- User profile guide: `docs/guides/USER_PROFILE.md`
- Product vision: `docs/product/VISION.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Authority model: `docs/knowledge/AUTHORITY.md`
- Historical Honcho setup: `docs/honcho-setup.md`
