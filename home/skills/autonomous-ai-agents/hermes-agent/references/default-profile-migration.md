# Default Profile Migration — From Named Profile to Custom HERMES_HOME

## Context

In Aether Agents v0.8.3, the orchestrator was migrated from the named profile `profiles/orchestrator/` to the default profile (root `home/` directory). This document captures the pattern for future migrations.

## Architecture Comparison

| Aspect | Named Profile (`-p orchestrator`) | Default Profile (custom HERMES_HOME) |
|--------|-----------------------------------|---------------------------------------|
| Config location | `home/profiles/orchestrator/config.yaml` | `home/config.yaml` |
| SOUL.md location | `home/profiles/orchestrator/SOUL.md` | `home/SOUL.md` |
| .env location | `home/profiles/orchestrator/.env` | `home/.env` |
| auth.json location | `home/profiles/orchestrator/auth.json` | `home/auth.json` |
| agent-hooks | `home/profiles/orchestrator/agent-hooks/` | `home/agent-hooks/` |
| Shell hooks | `home/profiles/orchestrator/shell-hooks-allowlist.json` | `home/shell-hooks-allowlist.json` |
| Wrapper script | `hermes -p orchestrator "$@"` | `hermes "$@"` |
| MCP DB | `home/.olympus/olympus_v3.db` (shared) | `home/.olympus/olympus_v3.db` (shared) |
| .aether | `home/.aether/` (shared) | `home/.aether/` (shared) |
| Daimon profiles | `home/profiles/hefesto/` etc. | `home/profiles/hefesto/` etc. |

## Migration Checklist

### Pre-migration
1. [ ] Verify default profile directory (`home/`) has no conflicting live config
2. [ ] Back up current named profile: `cp -r home/profiles/orchestrator/ /tmp/orchestrator-backup/`
3. [ ] Verify `HERMES_HOME` in wrapper script points to `home/`
4. [ ] Verify `.olympus/` DB path resolution (should resolve to `home/.olympus/`)

### Migration Steps
1. [ ] Copy SOUL.md from named profile to default: `cp home/profiles/orchestrator/SOUL.md home/SOUL.md`
2. [ ] Merge config.yaml: Copy named profile config to `home/config.yaml`
3. [ ] Merge .env: Add all keys from named profile .env to `home/.env`
4. [ ] Merge auth.json: Copy named profile auth to `home/auth.json` (if larger)
5. [ ] Copy agent-hooks: `cp -r home/profiles/orchestrator/agent-hooks/ home/agent-hooks/`
6. [ ] Copy shell-hooks-allowlist.json
7. [ ] Update wrapper script: Remove `-p orchestrator` flag, just `exec hermes "$@"`
8. [ ] Test: Run `hermes` without `-p` flag and verify SOUL.md loads correctly
9. [ ] Delete named profile directories: `rm -rf home/profiles/orchestrator/ home/profiles/hermes/`

### Post-migration Cleanup
1. [ ] Update .gitignore: Remove orphaned `profiles/hermes/` and `profiles/orchestrator/` entries
2. [ ] Add home-level runtime paths to .gitignore (agent-hooks/, pastes/, cron/, sandboxes/, etc.)
3. [ ] Update setup.sh version and wrapper template
4. [ ] Verify all Daimon profiles still work: `hermes -p hefesto`, `hermes -p etalides`, etc.
5. [ ] Run `hermes doctor` to check system health

## Pitfalls

### Reserved Profile Name "hermes"
The name "hermes" is in `_RESERVED_NAMES` ("hermes", "default", "test", "tmp", "root", "sudo"). Creating a profile called `hermes` causes crashes. If you need to use the orchestrator, either:
- Use the default profile (recommended with custom HERMES_HOME)
- Use a different name (e.g., "morfeo", "orchestrator")

### Agent-hooks Reference Trap
If `config.yaml` references `profiles/orchestrator/agent-hooks/block-write-commands.sh` and you delete that profile without moving the hooks, the write-restriction silently breaks. Always verify `agent-hooks` path in config.yaml after migration.

### MCP DB Path
The olympus_v3 DB MUST be at `HERMES_HOME/.olympus/olympus_v3.db` (or `AETHER_HOME/.olympus/`). It's shared across all Daimon profiles. Do NOT put it inside a profile directory.

### Template Drift
After deleting a named profile, its `config.yaml.template` is also gone. If setup.sh references it, update the template generation logic. Live configs are gitignored and auto-generated from templates.

### .gitignore Migration Gap
When moving runtime files from `profiles/orchestrator/` to `home/`, the `.gitignore` patterns change scope. Patterns like `home/profiles/*/agent-hooks/` only match inside profile directories — they don't cover `home/agent-hooks/`. After migration, add home-level equivalents: `home/agent-hooks/`, `home/pastes/`, `home/cron/`, `home/sandboxes/`, `home/shell-hooks-allowlist.json`, `home/shell-hooks-allowlist.json.lock`, `home/skills/.curator_backups/`, `home/skills/.usage.json`, `home/skills/.usage.json.lock`, `home/profiles/*/lsp/`. Also remove orphaned entries for deleted profiles.

### Broken Skill Directory Structure
When migrating skills between directories, verify the structure follows `<category>/<skill-name>/SKILL.md` (not `<skill-name>/<skill-name>/SKILL.md`). A nested directory causes `skills_list` and `skill_view` to fail silently — the skill becomes invisible. After any file reorganization, run `skill_view(name='<skill-name>')` to confirm detection.

### Daimon Config.yaml Must Exist
After gitignoring live `config.yaml` files (v0.8.1+), Daimons that lack a generated `config.yaml` will silently fail on delegation: `{thoughts: 0, messages: 0, tool_calls: 0, status: "completed"}`. Always run `scripts/setup.sh` after cloning or cleaning, and verify `home/profiles/*/config.yaml` and `home/config.yaml` exist before delegating.