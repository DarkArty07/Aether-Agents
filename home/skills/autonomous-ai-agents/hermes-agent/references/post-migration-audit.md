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

### 4. Fix in Priority Order

1. Source code (functional bugs — things break if not fixed)
2. Agent SOUL.md files (agents follow wrong paths)
3. Website and docs (users follow wrong instructions)
4. Skill references (portability)
5. Verify with the same grep patterns after fixes

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

### 6. Verify Clean State

After all fixes, re-run the grep suite. The only remaining references should be in CHANGELOG (historical) and gitignored runtime files (session JSONs).

```bash
# Final verification — should return empty for source, SOULs, website
grep -rn "OLD_PATTERN" src/ website/ home/profiles/*/SOUL.md home/SOUL.md \
  --include="*.py" --include="*.html" --include="*.md" 2>/dev/null
```

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

### Database path migrations

When a module's database path changes (e.g., `.eter/.consulting/` → `.aether/.consulting/`):
1. Update the source code path constant
2. Migrate the physical database file
3. Verify the new path works (open/close the DB)
4. Delete the old directory only after confirmation
