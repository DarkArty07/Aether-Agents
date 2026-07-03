# Batch PR Cleanup — Autonomous Sweep

When the task is "review all open PRs and merge the safe ones in a single pass," follow this checklist.

## Phase 1: Discovery

List ALL open PRs with enough metadata for classification:

```bash
gh pr list --state open --json number,title,headRefName,baseRefName,isDraft,mergeable,statusCheckRollup,author,createdAt --limit 50
```

## Phase 2: Classification

For each PR, classify into one of three categories:

| Criteria | ✅ SEGURO | ⚠️ REVISAR ANTES | ❌ NO TOCAR |
|----------|-----------|------------------|-------------|
| Not draft | ✅ | ❌ if draft | ❌ |
| Base = main | ✅ | ❌ if other target | ❌ |
| Mergeable = MERGEABLE | ✅ | ❌ if has conflicts | ❌ |
| CI passing OR pre-existing failure | ✅ | ❌ if CI failing AND new | ❌ |
| No sensitive files | ✅ | ❌ if touches secrets | ❌ if secrets |
| Author = repo owner | ✅ | ❌ if unknown author | ❌ if suspicious |
| No config.yaml changes | ✅ | ✅ | ❌ if config yaml |

**Sensitive files to check:** `home/.env`, `.env`, `auth.json`, `*.key`, `*.pem`, `secrets/`, `.git/config`

**Config files to flag (Chris decision):** `home/config.yaml`, `home/profiles/*/config.yaml`

### Distinguishing Pre-existing CI Failures

Before classifying a PR as ⚠️ due to CI failure, check if the failure is pre-existing on main:

1. Check the latest CI run on the PR branch — note which check name failed and the error
2. Check the latest CI run on main: `gh run list --branch main --limit 1 --json conclusion,workflowName`
3. If main also fails with the same check, view the failure log: `gh run view <RUN_ID> --log-failed`
4. Compare errors — if identical (same file, same line, same message), the failure is pre-existing

**Heuristic:** If the PR only touches docs, config templates, setup scripts, or skill files — and the CI failure is a lint/test error in `src/` — it is almost certainly pre-existing and orthogonal.

## Phase 3: Execution Order

For each ✅ or ⚠️(pre-existing CI) PR, in order:

### 3a. Self-approval check

```bash
PR_AUTHOR=$(gh pr view N --json author --jq .author.login)
GH_USER=$(gh api user --jq .login)
if [ "$PR_AUTHOR" = "$GH_USER" ]; then
  echo "Self-PR — skipping approval, merging directly"
else
  gh pr review N --approve --body "Approved via batch cleanup. Reviewed: [safety criteria]"
fi
```

### 3b. Pre-merge working tree check

```bash
if [ -n "$(git status --porcelain)" ]; then
  git stash push -m "batch-merge-autostash-$(date +%s)"
  NEED_POP=true
else
  NEED_POP=false
fi
```

### 3c. Squash merge + delete branch

```bash
gh pr merge N --squash --delete-branch 2>&1 || true
```

### 3d. Verify merge state

```bash
gh pr view N --json state,mergedAt
# Expected: {"state":"MERGED","mergedAt":"2026-06-05T00:50:14Z"}
```

## Phase 4: Post-Merge Sync

After ALL PRs are processed:

```bash
# Switch to main
git checkout main

# Pull latest
git pull origin main

# Prune stale remote tracking refs
git fetch --prune origin

# Verify all merged remote branches were deleted
git branch -r | grep -v "main\|HEAD"

# Clean stale local branches (only ones whose remote was deleted)
git branch --merged | grep -v "main\|HEAD" | xargs -r git branch -d
```

## Phase 5: Final Verification

```bash
# Show recent commits
git log --oneline -5

# Check no stale feature branches remain
git branch | grep -v main
git branch -r | grep -v "main\|HEAD"

# Check tags (only if release was part of the sweep)
git tag -l | tail -5
```

## Anti-patterns

| Pattern | Why it's wrong | Better |
|---------|---------------|--------|
| Approving your own PR | GitHub rejects: "Can not approve your own pull request" | Skip approval, merge directly |
| Merging with unstaged changes | API merge succeeds but local git fails; remote branch not deleted | Stash first, merge, pop |
| Blindly trusting CI failure as PR-introduced | Blocks merges pre-existing failures unnecessarily | Cross-check against main first |
| Processing PRs out of order | Later PRs may depend on earlier ones; conflicts cascade | Process oldest first (by number or creation date) |
| Skipping post-merge sync | Local main stays behind; next session works on stale state | Always `git pull origin main` after batch merge |
