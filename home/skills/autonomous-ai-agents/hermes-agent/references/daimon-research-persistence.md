# Daimon Research Persistence Pattern

Etalides (and future research Daimons) use an Obsidian-flavored vault for web research persistence.

## Directory Structure

```
__AETHER_ROOT__/research/
├── .gitkeep
├── .obsidian/
│   ├── app.json          # Obsidian config (wikilinks, line breaks)
│   └── workspace.json    # Workspace layout
├── README.md              # Vault documentation
├── INDEX.md              # Auto-maintained index by date and tags
├── YYYY-MM-DD-HHMM-topic-slug.md   # Research files
└── ...
```

## File Format

Every research file has YAML frontmatter and wikilinks:

```markdown
---
date: 2026-05-19T14:30:00Z
author: etalides
depth: standard
confidence: high
model: deepseek-v4-flash
links_used: 8
links_budget: 10
tags: [framework, security, api]
---

# [Topic Title]

## Findings
- [Finding 1]: [concise, factual description]
- [Finding 2]: [concise, factual description]

## Sources
1. [URL or file path] — [what was extracted]

## Confidence: [high | medium | low]
- [justification]

## Limitations
- [what could not be found — omit if none]
```

## Separation from Agent Runtime

- Research files go in `__AETHER_ROOT__/research/` (project root, git-tracked)
- Agent runtime files (sessions, memories, state) go in `__AETHER_ROOT__/home/profiles/<agent>/` (gitignored)
- This separation means research persists across clones and is accessible to all agents

## Dual Persistence Model

| Research Type | Persisted? | Format | Where |
|---------------|-----------|--------|-------|
| **Web research** | Yes | Obsidian-flavored markdown | `__AETHER_ROOT__/research/YYYY-MM-DD-HHMM-topic-slug.md` |
| **Code research** | No | Direct response to Hermes in standard output format | N/A — situational |

Web research produces reusable knowledge ("how does framework X work?"). Code research answers situational questions ("how is X implemented in this project?"). Persisting situational answers creates noise in the knowledge base.

## Keywords and Wikilinks

Use `[[YYYY-MM-DD-topic-slug]]` to connect related research files. The INDEX.md maintains two views:
- **By Date** — chronological listing
- **By Tag** — thematic grouping using frontmatter `tags`

## Template Paths

In `config.yaml.template`, use `__AETHER_ROOT__` placeholders:
```yaml
link_budget:
  max_links: 10
  fast_mode: 5
```

In SOUL.md, reference: `__AETHER_ROOT__/research/YYYY-MM-DD-HHMM-topic-slug.md`

The `setup.sh` script replaces `__AETHER_ROOT__` with the actual project path during configuration.