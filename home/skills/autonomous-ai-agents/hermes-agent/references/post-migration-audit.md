# Post-Migration Stale Reference Audit

When a project undergoes a major migration (path changes, module renames, profile reorganization, convention shifts), stale references to old paths/names survive in source code, docs, website, and config templates. This is the systematic methodology for finding and fixing them.

## When to Run This Audit

- After migrating from one install method to another (git-clone → pip install)
- After renaming or removing directories (profiles, modules, scripts)
- After changing path conventions (`.eter/` → `.aether/`, `profiles/hermes/` → default profile)
- After deprecating scripts or tools (configure.sh → setup.sh)
- Before tagging a release that includes any of the above

## Audit Steps

### 1. Catalog the Old Conventions

List every old path, name, or convention that changed. Examples from the Aether Agents v0.8.x migrations:

| Old Convention | New Convention | Type |
|---------------|---------------|------|
| `.eter/` | `.aether/` | Path convention |
| `profiles/hermes/` | default profile (`home/`) | Directory structure |
| `profiles/orchestrator/` | default profile (`home/`) | Directory structure |
| `olympus_v2` | `olympus_v3` | Module name |
| `configure.sh`, `start.sh` | `setup.sh`, `start-gateway.sh` | Script names |
| `.pi-daimons/` | ACP (no directory) | Architecture change |
| `~/.hermes/` | `__AETHER_ROOT__/home` | Config path |
| Hardcoded `/home/user/` | `__AETHER_ROOT__` placeholders | Template pattern |

### 2. Grep for Each Old Convention

Run targeted greps across all tracked file types. Exclude git internals, venvs, and node_modules:

```bash
cd /path/to/project

# For each old convention:
grep -rn "OLD_PATTERN" \
  --include="*.md" --include="*.sh" --include="*.py" \
  --include="*.yaml" --include="*.yml" --include="*.toml" \
  --include="*.html" --include="*.json" --include="*.txt" \
  . 2>/dev/null | grep -v ".git/" | grep -v ".venv" | grep -v "node_modules"
```

Check source code separately (highest priority — functional bugs):

```bash
grep -rn "OLD_PATTERN" src/ --include="*.py"
```

### 3. Classify Each Finding

| Category | Priority | Action | Example |
|----------|----------|--------|---------|
| **Functional code** — path used at runtime | CRITICAL | Must update | `consulting_db.py: db_path = Path(root) / ".eter" / ...` |
| **Agent SOUL.md** — instructions agents follow | CRITICAL | Must update | `SOUL.md: "Write state to PROJECT_ROOT/.eter/..."` |
| **Website/docs** — user-facing instructions | HIGH | Must update | `setup.html: cp profiles/hermes/.env ...` |
| **Skill references** — portable examples | HIGH | Must update | `SKILL.md: /home/user/project/profiles/hermes/...` |
| **CHANGELOG** — historical record | LOW | Do NOT change | "Removed `src/olympus_v2/`" stays as-is |
| **Session JSON** — runtime state | SKIP | Gitignored, expires naturally | Daimon session files |

**Key pitfall:** A blanket `sed -i 's/old/new/g'` replaces ALL categories. Lines like "Removed `.eter/`" become "Removed `.aether/`" — making it look like the ACTIVE convention was deleted. Always do selective replacement per category.

### 4. Fix in Priority Order (Multi-Pass)

A single pass never catches everything. Expect 3-4 passes where each pass finds references missed by the previous one. Reasons: (a) fixing one file draws attention to nearby stale refs, (b) different file categories need different grep patterns, (c) skill subdirectories are easy to miss, (d) source code comments vs functional paths need different treatment.

**Pass pattern:**
1. Source code (functional bugs — things break if not fixed)
2. Agent SOUL.md files (agents follow wrong paths)
3. Website and docs (users follow wrong instructions)
4. Skill references (portability — deep subdirectories, often missed)
5. Re-run the full grep suite → catches what pass 1-4 missed
6. Commit → re-scan → another pass if needed

**Why multi-pass works:** After committing fixes, the diff itself reveals context you skimmed over. Reading the changed files fresh often surfaces adjacent stale references. The Aether Agents v0.8.5 audit took 4 passes to reach zero functional stale refs.

### 5. Migrate On-Disk State

If the old directory still exists on disk (legacy state, databases), migrate it:

```bash
# Example: .eter/ → .aether/
mkdir -p .aether/.consulting/
cp .eter/.consulting/consulting.db .aether/.consulting/
ls -la .aether/.consulting/consulting.db  # verify
rm -rf .eter/  # only after verification
```

**Pitfall:** Code that references the old path may still work because the old directory exists on disk. This creates a false sense of correctness. The code works *by accident*, not by design. Only deleting the old directory reveals the bug — so always migrate first, then delete.

### 6. Prune Stale Branches

Migrations often produce feature branches that are merged or abandoned. Clean up local and remote:

```bash
# List all local branches
git branch

# List all remote branches
git branch -r

# Delete merged local branches
git branch -d feature/migration-cleanup
git branch -D fix/abandoned-experiment  # force-delete unmerged

# Prune remote branches that no longer exist on origin
git remote prune origin

# Delete specific remote branches (if you have push access)
git push origin --delete feature/old-branch
```

**Caution:** Some remote branches may be intentionally kept (dependabot PRs, release branches, long-lived feature branches). Check with the team before deleting remote branches you didn't create.

### 7. Verify Clean State

After all fixes, re-run the grep suite. The only remaining references should be in CHANGELOG (historical) and gitignored runtime files (session JSONs).

```bash
# Final verification — should return empty for source, SOULs, website
grep -rn "OLD_PATTERN" src/ website/ home/profiles/*/SOUL.md home/SOUL.md \
  --include="*.py" --include="*.html" --include="*.md" 2>/dev/null
```

### 8. Commit Strategy

Use atomic commits per category — one commit per convention being migrated. This makes rollback easy if a replacement introduces a bug:

```bash
git commit -m "fix: .eter→.aether path references in source and agent configs"
git commit -m "fix: profiles/hermes→default profile references in docs and website"
git commit -m "chore: remove stale branches and dead directories"
```

**Do NOT** use a single monolithic commit for a multi-convention migration — if you need to revert one convention, you'd have to revert everything.

## Common Patterns

### Hardcoded user paths → Placeholders

```bash
# Find hardcoded user paths in tracked docs (not templates)
grep -rn '/home/[^/]*/' --include='*.md' --include='*.yaml' --include='*.html' . \
  | grep -v '.template' | grep -v 'CHANGELOG'
```

Replace with `__AETHER_ROOT__` or equivalent placeholder that `setup.sh` resolves.

### Deleted profiles still referenced

After deleting `profiles/hermes/` or `profiles/orchestrator/`:
1. Check website HTML for paths
2. Check skill references for examples
3. Check config.yaml templates for include paths
4. Check systemd service files (if any)

### Skill subdirectories are easy to miss

Skills live in `home/skills/<category>/<name>/` — often 3-4 levels deep. A grep at the project root will find them, but manual file-by-file review often skips them. In the v0.8.5 audit, the first 3 passes missed stale `profiles/hermes/` references inside skill SKILL.md files because they were in `home/skills/autonomous-ai-agents/hermes-agent/SKILL.md` (a 400+ line file with references scattered across 5 locations).

### README positioning when project extends a framework

When a project is built as an extension of another framework (e.g., Aether Agents extends hermes-agent), the README must explain the relationship clearly. The pattern:

1. **Tagline** — Name the foundation framework explicitly: _"A multi-agent team built on hermes-agent"_
2. **"What is X?" block** — Two paragraphs: first explains the base framework, second explains what the extension adds
3. **Architecture diagram** — Show instances of the base framework (Daimons = hermes-agent processes) rather than abstract boxes
4. **Key Features row 1** — Lead with the framework dependency to set expectations

This prevents confusion where visitors think the project is standalone or re-implements what the base framework provides.

**Tip:** After the initial grep sweep, do a targeted second sweep specifically for skill directories:
```bash
grep -rn "OLD_PATTERN" home/skills/ --include="*.md" --include="*.sh" --include="*.py"
```

### Database path migrations

When a module's database path changes (e.g., `.eter/.consulting/` → `.aether/.consulting/`):
1. Update the source code path constant
2. Migrate the physical database file
3. Verify the new path works (open/close the DB)
4. Delete the old directory only after confirmation

### Config template references to non-existent docs

`.env.example` and `config.yaml.template` files often reference documentation files that no longer exist (or were renamed). Example from v0.8.5: five Daimon `.env.example` files referenced `PROVIDERS.md` which had been renamed to `CONFIGURATION.md`. These aren't functional bugs (templates don't run), but they confuse users who follow the reference and find nothing.

**Pattern:**
```bash
# Find doc references in config templates
grep -rn '\.md' home/profiles/*/.env.example home/profiles/*/config.yaml.template \
  --include="*.example" --include="*.template" 2>/dev/null
```

For each reference found, verify the file exists:
```bash
for doc in $(grep -oh '[A-Za-z_]*\.md' home/profiles/*/.env.example | sort -u); do
  find . -name "$doc" -not -path "./.git/*" 2>/dev/null || echo "MISSING: $doc"
done
```

### Source code comments with stale paths

Comments referencing old paths aren't functional bugs but confuse future developers who search for paths and find outdated references. They often survive multiple audit passes because grep patterns focus on code, not comments.

**Pattern:**
```bash
# Find path-like references in comments
grep -rn '#.*profiles/hermes\|#.*\.eter\|#.*~/.hermes/' src/ --include="*.py" 2>/dev/null
```

In the v0.8.5 audit, `acp_manager.py` line 132 and `config_loader.py` line 63 both had comments referencing `profiles/hermes/orchestrator` — these were missed in the first 3 passes because they were comments, not code.

**Treatment:** Update comments to reflect current architecture. Change `profiles/hermes/orchestrator` to `home dir (default profile)` or similar. Don't delete informative comments — update them.

### Makefile and CI version strings

Makefiles and CI workflow files often contain version strings or action versions that lag behind. These are easy to miss because they live outside the main source tree.

**Pattern:**
```bash
# Check version consistency across key files
grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' Makefile pyproject.toml README.md scripts/setup.sh | sort | uniq -c

# Check CI action versions
grep -rn 'uses:.*@v[0-9]' .github/workflows/
```

In the v0.8.5 audit, `Makefile` referenced v0.8.0 while `pyproject.toml` was at v0.8.5, and `deploy-site.yml` used `upload-pages-artifact@v3` (outdated).

### Post-migration MCP tool verification

After any migration that touches MCP server paths, database locations, or Daimon profile configs, verify that every MCP tool still works end-to-end. Functional tests catch bugs that grep cannot — the `.eter→.aether` migration left all source references correct but the physical database hadn't been migrated yet, which only surfaced when tools were actually invoked.

**Verification checklist:**

| MCP Tool | What to test | Pass criteria |
|----------|-------------|---------------|
| `aether_status` | Read with `detail=full` | Returns hot_state with correct phase, task, session count |
| `aether_update` | Test all sub-actions: `set_phase`, `set_task`, `add_decision`, `add_issue`, `resolve_issue`, `add_blocker`, `remove_blocker` | Each returns success confirmation; verify in DB with `sqlite3 .aether/aether.db` |
| `aether_curate` | Run with `focus=recent` | CONTEXT.md regenerated, size <1,500 chars, reflects current state |
| `discover` | List available agents | Returns all expected agents with correct `profile_path` |
| `delegate` | Send a trivial task to a Daimon (e.g., create+verify a test file) | Returns `status: completed` with non-zero `tool_calls` and `messages` |

**Pitfall — aether_curate staleness:** `aether_curate` reads the DB at the time it runs. If you call `aether_update(set_task, ...)` AFTER a `curate`, the CONTEXT.md will contain the OLD task until the next curate. Always run `aether_curate` AFTER all `aether_update` calls to get the current state reflected. The DB itself is always correct — only the CONTEXT.md cache can be stale.

**Cleanup after testing:** Remove any test artifacts (decision id for test, test issue, test files). Restore the phase/task to their real values before testing. If you created a test decision or issue, resolve it rather than deleting — the DB auto-increments IDs and gaps are normal.
