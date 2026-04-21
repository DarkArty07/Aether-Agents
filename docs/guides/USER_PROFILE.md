# User Profile Guide

## Overview

The `USER.md` file tells Hermes (and other Daimons) who you are and how you like to work. It lives in:

```
home/profiles/hermes/memories/USER.md
```

This file is **personal** — it is loaded into the Hermes context at runtime and adapts the entire Aether Agents experience to your preferences. It is **not** meant to be shared or committed to public repositories.

## What Goes in USER.md

### Communication Preferences
- **Language**: What language you interact in (e.g., `Spanish`, `English`, `Portuguese`)
- **Response style**: Do you prefer concise answers or detailed explanations?
- **Tone**: Casual, formal, technical?

### Workflow Preferences
- **Tool preferences**: Do you prefer certain tools or workflows? (e.g., delegate_task vs external agents)
- **Decision style**: Do you want to approve every decision, or let Hermes decide on trivial things?
- **Iteration style**: Do you prefer to iterate together, or get a complete solution in one shot?

### Things to Avoid
- Patterns or approaches you've found don't work for you
- Over-engineering preferences
- Tooling you dislike

### Personal Context
- Your role (developer, designer, manager, etc.)
- Projects you're working on
- Timezone (useful for scheduling and context)
- Any accessibility needs

## Best Practices

1. **Keep it concise** — USER.md is injected into every conversation. Long files waste context. Aim for 10-15 lines max.

2. **Write declarative facts, not instructions** — Instead of "Always respond in Spanish", write "Interacts in Spanish". The Daimons will pick it up.

3. **Use paragraph separators** — Use `§` on its own line to separate unrelated facts. This helps the Daimons parse distinct topics.

4. **Update when preferences change** — If you correct a Daimon multiple times on the same thing, add it to USER.md so it sticks.

5. **Don't duplicate SOUL.md** — SOUL.md defines the agent's identity and rules. USER.md defines your preferences. Keep them separate.

6. **Avoid sensitive data** — No API keys, passwords, or personal identifiable information. USER.md is a plain text file.

## Example USER.md

```markdown
# User Profile

Alex — interacts in English. Prefers concise responses. Senior backend developer.
§
Prefers delegate_task for coding tasks. Uses Claude Code only for complex multi-step plans.
§
Dislikes over-engineering. Prefers simple solutions over clever abstractions.
§
Works in PST timezone. Active on GitHub — prefers PR-based workflow.
```

## Related Files

| File | Purpose |
|------|---------|
| `home/profiles/hermes/memories/USER.md` | Your personal preferences (this file) |
| `home/profiles/hermes/memories/MEMORY.md` | Hermes' notes about your environment and projects |
| `home/profiles/<daimon>/SOUL.md` | Identity and rules for each Daimon |

## FAQ

**Q: Is USER.md committed to git?**
A: The template is. Your personal USER.md should be in `.gitignore` or treated as local-only. The repo ships with an empty template.

**Q: Can other Daimons read USER.md?**
A: Only Hermes reads USER.md directly. When Hermes delegates to other Daimons, relevant context is included in the delegation prompt.

**Q: How is USER.md different from MEMORY.md?**
A: USER.md is about *you* (your preferences, language, style). MEMORY.md is about *the environment* (project paths, tool versions, conventions). Both persist across sessions.
