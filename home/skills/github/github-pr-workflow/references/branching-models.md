# Branching Models — When to Use dev vs. feature → main Direct

## Model A: feature → dev → main (Classic Integration Branch)

```
feature/{name}  →  dev  →  main
```

**Use when:**
- Multiple developers working concurrently, need a shared integration branch
- Complex project with CI pipelines that need a staging environment
- Releases are infrequent and require QA on `dev` before promotion
- Team culture prefers review-on-review (feature → dev PR, then dev → main PR)

**Rules:**
1. Branch from `dev`, merge back to `dev`
2. `dev` receives all feature PRs; `main` only receives release merges from `dev`
3. After release merge, `dev` and `main` must be at same commit
4. Delete feature branches after merging

**Drawbacks:**
- Extra merge step per release
- `dev` can drift from `main` if not maintained
- More branches to track

## Model B: feature → main (Simplified, No Integration Branch)

```
feature/{name}  →  main
```

**Use when:**
- Solo developer or small team (1-3 people)
- Frequent small releases, no staging environment needed
- Project is stable enough that `main` is always deployable
- Want minimal branch overhead

**Rules:**
1. Branch from `main`, merge back to `main` via PR
2. Never commit directly to `main`
3. Delete feature branches after merging

**Advantages:**
- Fewer merges, cleaner history
- `main` is always the source of truth
- No integration branch to maintain

## Migration: dev → main Direct

To eliminate `dev` and switch to Model B:

```bash
# 1. Fast-forward main to dev (if dev is ahead)
git checkout main
git merge --ff-only dev

# 2. Push updated main
git push origin main

# 3. Delete dev everywhere
git branch -D dev
git push origin --delete dev

# 4. Update AGENTS.md / CONTRIBUTING.md / README.md
#    to reflect the new branching model

# 5. Future: branch from main
git checkout main && git pull origin main
git checkout -b feature/new-thing
```

**Before migration, check:**
- Are there open PRs targeting `dev`? Retarget them to `main` first.
- Are there feature branches based on `dev`? Rebase them onto `main`.
- Is CI configured to trigger on `dev` pushes? Update CI config.

## Pitfall: Merging with Uncommitted Local Changes

Before switching branches (checkout, merge, rebase), always check for local changes:

```bash
git status --short
```

If there are modified files (`M`) or untracked files (`??`) that you want to keep:

```bash
# Option A: Stash everything
git stash push -m "stash before <operation>"

# Option B: Commit first (if the changes are ready)
git add <files> && git commit -m "wip: <description>"

# Option C: Discard (if you don't need them)
git checkout -- <files>   # or git restore <files>
```

**Common scenario:** After recovering files from a backup branch, you may have local modifications to tracked files (e.g., a skill's SKILL.md). `git checkout main` will abort with "Your local changes... would be overwritten." Stash or commit first.

## Pitfall: Backup Recovery with Changed Directory Structure

When recovering work from an old backup branch or tag, the directory structure may have changed between versions.

**Example:** Backup has `home/skills/`, but current HEAD has `skills/` (repo root).

**Wrong:** Copy `home/skills/` directly → creates `home/skills/` in current HEAD, duplicating structure.

**Right:** Extract content to the current structure:
```bash
# Extract from backup to correct path
git show backup/pre-v0.13.0:home/skills/devops/kanban/SKILL.md > skills/devops/kanban/SKILL.md

# Or use git checkout with --pathspec-from-file for bulk
git checkout backup/pre-v0.13.0 -- home/skills/devops/kanban/
# Then move files to correct locations
mv home/skills/devops/kanban/* skills/devops/kanban/
rmdir home/skills/devops/kanban/
```

**Always verify destination paths match the current project structure before writing recovered files.**
