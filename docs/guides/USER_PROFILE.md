# User Profile Guide

> **Status:** CURRENT TARGET
> **Governing decision:** `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`

## Overview

`USER.md` is the compact, Hermes-managed profile describing who the user is and how they prefer to work.

```text
home/memories/USER.md
```

Hermes is the sole global profile custodian. It reads the user directly, detects durable preferences and recurring corrections, organizes them, removes stale entries, and passes only relevant context to Daimons.

The user may inspect and correct the profile, but they should not need to maintain it manually for Aether to personalize itself.

Aether does not use Honcho in the approved target architecture.

## What belongs in `USER.md`

### Durable communication preferences

- Preferred language.
- Desired level of detail.
- Tone and interaction style.
- Formatting preferences that apply across tasks.

### Durable workflow preferences

- Desired autonomy level.
- How decisions should be presented.
- Preferred collaboration and iteration style.
- Tools or approaches the user consistently prefers or rejects.

### Stable personal context relevant to work

- General role or experience level.
- Timezone.
- Accessibility needs.
- Stable constraints that materially affect software projects.

## What does not belong in `USER.md`

- Current task progress.
- Temporary instructions for one request.
- Commit hashes, issue numbers, release state, or milestone completion.
- Detailed project requirements or architecture.
- Passwords, tokens, credentials, or sensitive personal data.
- A Daimon's unverified interpretation of the user.
- Imperative instructions that could override a future request.

Project-specific vision and decisions belong in the project's version-controlled documentation. Hot project state belongs in `.aether`. Historical conversation detail belongs in session history.

## Hermes responsibilities

Hermes should:

1. Detect explicit preferences and repeated corrections.
2. Distinguish durable patterns from one-off requests.
3. Write compact declarative facts.
4. Deduplicate overlapping entries.
5. Correct or remove stale preferences.
6. Keep personal preferences separate from environment facts.
7. Give current explicit instructions precedence over stored memory.
8. Pass only relevant profile context to each Daimon.
9. Reject secrets and sensitive credentials from plain-text memory.
10. Preserve provenance when a preference originated from a specialist observation.

Daimons may report a possible preference to Hermes, but they do not independently own or rewrite the global user model.

## `USER.md` versus `MEMORY.md`

| File | Purpose |
|---|---|
| `home/memories/USER.md` | User identity, preferences, recurring corrections, and stable work style |
| `home/memories/MEMORY.md` | Stable environment facts, conventions, tool quirks, and durable operating context |
| Project documentation | Vision, requirements, scope, architecture, and durable product decisions |
| `.aether` | Current phase, active task, blockers, and hot project continuity |
| Skills | Reusable procedures and verified workflows |

A preference about how the user wants work performed belongs in `USER.md`. A stable fact about the environment belongs in `MEMORY.md`. A reusable procedure belongs in a skill.

## Writing style

Use concise declarative facts, not permanent commands.

```markdown
# User Profile

Christopher — interacts primarily in Spanish. Prefers direct, dense responses without filler.
§
Acts as product owner and does not want routine technical decisions pushed back to him.
§
Dislikes unrequested scope expansion and overengineering.
```

Avoid:

```markdown
Always answer in Spanish.
Never ask technical questions.
Always use framework X.
```

Imperative phrasing can be misread as authority over later explicit requests.

## Shared skills boundary

User-specific preferences normally remain in `USER.md` rather than being hard-coded into shared skills.

A shared skill may instruct an agent to consult the active user profile, but it should not encode one person's preferences as universal product behavior.

Whether Aether later supports private per-user skills remains an open design question.

## FAQ

### Is `USER.md` committed to Git?

The template may be versioned. A real user's profile should remain local and private unless the user explicitly chooses another storage model.

### Can Daimons read it directly?

The approved model gives Hermes direct custody. Hermes sends relevant context in the task contract or delegation. Daimons should not receive the entire global profile by default.

### What happens when the user changes a preference?

The current explicit instruction wins immediately. Hermes should then correct or supersede the stored profile so the stale preference does not return later.

### Does Aether use Honcho?

No. Honcho is excluded from the approved product and the v0.22.0 candidate has removed its tracked provider, setup, service, and operational-documentation surfaces. Historical decisions and release evidence remain available for traceability.
