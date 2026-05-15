# Project Context Files — Loading Mechanism & Cross-Tool Compatibility

## How Hermes Agent Loads Context Files

Hermes has **two independent systems** that load project context files.

### System 1: Startup Context (`agent/prompt_builder.py`)

Loaded **once** at session start into the system prompt. Priority is **first-match-wins** — only ONE context source is loaded.

```
Priority:
  1. .hermes.md / HERMES.md  →  Walks from cwd to git root (checks every parent dir)
  2. AGENTS.md / agents.md    →  Cwd only (no walk)
  3. CLAUDE.md / claude.md    →  Cwd only (no walk)
  4. .cursorrules + .cursor/rules/*.mdc  →  Cwd only (loads ALL .mdc files together)
```

Key behaviors:
- If `.hermes.md` is found in a parent directory, Hermes stops and does NOT check for `AGENTS.md`, `CLAUDE.md`, or `.cursorrules`.
- `.cursorrules` and `.cursor/rules/*.mdc` are loaded TOGETHER (not one or the other).
- Each source is truncated to **20,000 chars** (70% head, 20% tail, 10% marker).
- `.hermes.md` supports **YAML frontmatter** (`---` delimited) which is stripped by `_strip_yaml_frontmatter()`. Reserved for future use.
- SOUL.md from HERMES_HOME is **independent** — always included, not part of the priority chain.
- Content is scanned for prompt injections via `_scan_context_content()`.

### System 2: Subdirectory Hints (`agent/subdirectory_hints.py`)

Loaded **during conversation** when tools access files in new directories. Injected as a suffix on tool results (NOT in system prompt). This preserves prompt caching.

Key differences from Startup Context:
- Searches for `AGENTS.md`, `agents.md`, `CLAUDE.md`, `claude.md`, `.cursorrules` in subdirectories.
- Does NOT search for `.hermes.md` (startup-only).
- Loads ALL found hints (not first-match-wins globally), but **first-match-wins per directory**.
- Truncated to **8,000 chars** (more aggressive than startup's 20K).
- Walks ancestors up to **5 levels** above the accessed file.
- Tracks loaded directories to prevent re-loading.
- `.cursor/rules/*.mdc` is NOT searched in subdirectories (only flat `.cursorrules`).

Example flow:
```
Agent reads src/olympus_v3/server.py
→ SubdirectoryHintTracker detects src/olympus_v3/ is new
→ Searches for AGENTS.md in src/olympus_v3/ (not found)
→ Searches for AGENTS.md in src/ (not found)
→ Searches for AGENTS.md in project root (found!)
→ Injects content as suffix on the read_file tool result
→ Marks project root as loaded (won't re-discover)
```

### YAML Frontmatter Support (`.hermes.md` only)

```yaml
---
model: anthropic/claude-sonnet-4
tools:
  - web
  - file-read
---

# Project Rules
...markdown content...
```

Frontmatter is **extracted** (not injected into the prompt). Reserved for future use — currently stripped before content is loaded.

### `_scan_context_content()` Security

All loaded context files pass through a security scan that detects prompt injection attempts. This prevents malicious repos from injecting instructions via their `AGENTS.md` or `.cursorrules`.

## Cross-Tool Compatibility Comparison

| Aspect | Hermes Agent | Claude Code | Cursor |
|--------|-------------|-------------|--------|
| Primary file | `.hermes.md` / `AGENTS.md` | `CLAUDE.md` | `.cursor/rules/*.mdc` |
| Priority | First-match-wins (1 of 4) | Aditivo (all stack) | Priority order |
| Dir walk | `.hermes.md` walks to git root | Walks + subdirs on-demand | `.mdc` globs per-dir |
| Subdirectory hints | Yes (on-demand, 8K) | Yes (on-demand) | Yes (globs match) |
| User-level | `HERMES_HOME/SOUL.md` | `~/.claude/CLAUDE.md` | Settings > Rules |
| Local/personal | No | `CLAUDE.local.md` (gitignored) | No |
| Char limit | 20K startup, 8K hints | No explicit limit | Context window |
| YAML frontmatter | Yes (`.hermes.md` only) | No | Yes (`.mdc` files) |
| `/init` auto-generate | **No** | **Yes** (`/init` command) | `/create-rule` in chat |

## Recommendation: Use `AGENTS.md`

For projects shared across multiple AI tools, `AGENTS.md` is the **only format natively supported by all three**:

| Format | Hermes | Cursor | Claude Code |
|--------|--------|--------|-------------|
| `.hermes.md` | ✅ Priority 1 | ❌ | ❌ |
| `AGENTS.md` | ✅ Priority 2 | ✅ Native | ✅ Native |
| `CLAUDE.md` | ✅ Priority 3 | ❌ | ✅ Native |
| `.cursor/rules/*.mdc` | ✅ Priority 4 | ✅ Native | ❌ |

Benefits of `AGENTS.md`:
- **Visible** — doesn't start with a dot, appears in `git status` and directory listings
- **Universal** — read by Hermes, Cursor, and Claude Code without any configuration
- **Standard** — Cursor promotes it as the simple alternative to `.cursor/rules/`
- **Subdirectory support** — Hermes loads it on-demand in subdirs via SubdirectoryHintTracker

**Do NOT place both `.hermes.md` and `AGENTS.md` in the same project** — `.hermes.md` wins and `AGENTS.md` is silently ignored at startup.

## Hermes Agent Does NOT Have `/init`

Unlike Claude Code (which has `/init` to auto-generate `CLAUDE.md` from codebase analysis), Hermes Agent does not have an equivalent command. Context files must be created manually. A future contribution could add `hermes init` that analyzes the codebase and generates an `AGENTS.md` scaffold.