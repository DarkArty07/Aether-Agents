# Athena Document Verification Protocol

## Overview
Athena is the QA Auditor Daimon. When verifying documentation, she checks:

1. **Accuracy** — Claims match code behavior
2. **Completeness** — All relevant sections present
3. **Consistency** — No contradictions within the document
4. **Currency** — No stale references to removed/renamed files

## Verification Checklist

### For README/INSTALLATION changes:
- [ ] Version numbers match actual release tags
- [ ] CLI commands match actual `hermes` subcommands
- [ ] File paths match current directory structure
- [ ] No references to deleted files (e.g., `profiles/hermes/`, `profiles/orchestrator/`)
- [ ] No references to deprecated scripts (e.g., `configure.sh`, `start.sh`)
- [ ] Environment variables match `.env.example` templates

### For config.yaml templates:
- [ ] Placeholders use `__AETHER_ROOT__` and `__HERMES_PYTHON__` (not hardcoded paths)
- [ ] `api_mode: chat_completions` is present
- [ ] MCP server configs match actual server entry points
- [ ] Daimon model names are current

### For SKILL.md files:
- [ ] YAML frontmatter has all required fields (name, description, category, version)
- [ ] References point to files that actually exist
- [ ] No broken internal links

## Output Format

Athena should return:
```
VERIFICATION: PASS|FAIL
ISSUES:
- [CRITICAL|WARNING|INFO] description
FIXES:
- suggested fix for each issue
```