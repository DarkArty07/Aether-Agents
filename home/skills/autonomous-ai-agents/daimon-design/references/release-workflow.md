# Aether Agents Release Workflow

## Pre-Release Checklist

1. **Verify CHANGELOG completeness** — Run `git tag -l` and compare tags against CHANGELOG headings. Tags can exist with GitHub releases but no CHANGELOG entry (v0.9.0 was missing). Fill any gaps before proceeding.

## Version Locations (must all be updated)

| File | What to change |
|------|---------------|
| `CHANGELOG.md` | Add new version section at top under `# Changelog` |
| `pyproject.toml` | `version = "X.Y.Z"` |
| `README.md` | Version badge URL (shields.io) |
| `scripts/setup.sh` | `SCRIPT_VERSION` variable |
| `AGENTS.md` | Version history table (if it exists) |

## Release Sequence

### For each release (repeat for each version if doing multiple):

```
1. Update CHANGELOG.md — insert new section before the previous version heading
   - Include: ### Changed, ### Fixed, ### Added, ### Removed subsections as needed
   - Follow existing format: `## [X.Y.Z] — YYYY-MM-DD`

2. Bump version in all version locations (see table above)

3. Commit: git commit -am "release: vX.Y.Z — description"

4. Merge dev → main:
   - git checkout main
   - git merge dev  (or git merge --ff-only dev if fast-forward)
   - Resolve any conflicts with care

5. Tag: git tag -a vX.Y.Z -m "vX.Y.Z — one-line description"

6. Push: git push origin main --tags && git push origin dev

7. GitHub Release:
   - Use `gh release create vX.Y.Z` with `--title` and `--notes-file` or inline `--notes`
   - Title format: `vX.Y.Z — Short Description`
   - Body: copy from CHANGELOG entry, formatted for readability
```

### Multiple releases in one session:

If releasing v0.10.0 and v0.10.1 together:
1. Do v0.10.0 release first (merge dev → main, tag, push, GitHub release)
2. Then create feature branch for v0.10.1 changes on dev
3. Implement v0.10.1 changes
4. PR to dev, merge
5. Merge dev → main (again)
6. Tag v0.10.1, push, GitHub release

## CHANGELOG Format Convention

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Changed
- **Component: what changed** — details
  - Sub-detail if needed

### Fixed
- **Component: what was fixed** — details

### Added
- **New feature** — details

### Removed
- **What was removed** — reason
```

- Each bullet starts with `**Component:**` (bold component, colon)
- Sub-bullets use `- ` indentation
- Version comparison links: `[X.Y.Z]: https://github.com/DarkArty07/Aether-Agents/compare/vPREV...vX.Y.Z`

## Delegation Pattern

When delegating a release to Hefesto, include:
1. **EXACT CHANGELOG content** — paste the full section to insert, never describe it vaguely
2. **Version number** — explicitly state which version
3. **All files to bump** — list them with the exact change
4. **GitHub release body** — provide the full markdown body
5. **Branch strategy** — feature branch → dev → PR → merge dev → main → tag → release

Hefesto may also update files not explicitly listed if version strings appear in them (README badges, AGENTS.md, setup.sh). Verify the commit diff includes all expected changes.

## Pitfalls

- **CHANGELOG gap**: Tags can exist without CHANGELOG entries. Always verify before cutting a new release.
- **Template drift**: After updating live config.yaml, always update config.yaml.template too. They drift apart silently.
- **Merge conflicts**: When dev has diverged significantly from main, `git merge dev` may produce conflicts. The `--theirs` strategy resolves most conflicts correctly for version bumps, but review the result.
- **Stashed changes**: If Hefesto uses `git stash` during release, make sure stashed changes are restored on the correct branch afterward.