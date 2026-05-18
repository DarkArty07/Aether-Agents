---
name: github-pr-workflow
description: "GitHub PR lifecycle: branch, commit, open, CI, merge."
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review]
---

# GitHub Pull Request Workflow

Complete guide for managing the PR lifecycle. Each section shows the `gh` way first, then the `git` + `curl` fallback for machines without `gh`.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repository with a GitHub remote

### Quick Auth Detection

```bash
# Determine which method to use throughout this workflow
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  # Ensure we have a token for API calls
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
echo "Using: $AUTH"
```

### Extracting Owner/Repo from the Git Remote

Many `curl` commands need `owner/repo`. Extract it from the git remote:

```bash
# Works for both HTTPS and SSH remote URLs
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
echo "Owner: $OWNER, Repo: $REPO"
```

---

## 1. Branch Creation

This part is pure `git` — identical either way:

```bash
# Make sure you're up to date
git fetch origin
git checkout main && git pull origin main

# Create and switch to a new branch
git checkout -b feat/add-user-authentication
```

Branch naming conventions:
- `feat/description` — new features
- `fix/description` — bug fixes
- `refactor/description` — code restructuring
- `docs/description` — documentation
- `ci/description` — CI/CD changes

## 2. Making Commits

### Pitfall 1: Files Ignored by .gitignore (can't stage)

Some config files (e.g., `home/config.yaml`) are in `.gitignore` because they contain API keys or are machine-specific. If you need to commit a **structural configuration change** (like toolset definitions) that is not a secret, `git add` will silently skip it — no error, no warning, and the file won't appear in `git status`.

**Detect:** If `git diff <file>` and `git status <file>` show nothing but you know the file was modified, check `.gitignore`:
```bash
git ls-files <file>     # empty = not tracked, possibly ignored
git check-ignore -v <file>  # shows which rule ignores it
```

**Fix:** Force-track with `-f`:
```bash
git add -f path/to/ignored-file.yaml
```

**Caution:** Only force-track files whose content you've reviewed. Never force-add files that contain real secrets (hardcoded passwords, API keys as literal values). Files using `${ENV_VAR}` references for secrets are safe to track.

### Pitfall 2: Already-tracked files still staged despite .gitignore

Adding a file to `.gitignore` does **NOT** stop git from tracking changes to it if it was already committed. `git add -A` will happily stage modifications to a tracked file that matches `.gitignore` rules. This is a common source of accidentally committed secrets or runtime configs.

**Detect:** After staging, check for files that should be gitignored but appear in the diff:
```bash
# Show all staged files — scan for anything that should be local
git diff --cached --name-only

# Specifically check if a gitignored file is still tracked
git ls-files path/to/file.yaml   # non-empty = still tracked
```

**Fix:** Remove from the index (keeps the local file):
```bash
git rm --cached path/to/local-config.yaml
git commit -m "chore: stop tracking local config (already in .gitignore)"
```

After `git rm --cached`, future `git add -A` will correctly skip the file.

### Pitfall 3: Untracked runtime files staged by git add -A

When a project has accumulated runtime artifacts (SQLite databases, caches, session state, JSON dumps) that aren't in `.gitignore`, `git add -A` stages everything indiscriminately. Before committing any bulk staging:

1. **Audit untracked files before staging** — run `git status --short` and review `??` entries for runtime state
2. **Update `.gitignore` first** — add patterns for any runtime files/dirs discovered (e.g., `*.db`, `cache/`, `hindsight/`, `state-snapshots/`, `.curator_state`)
3. **Then `git add -A`** — newly gitignored files won't appear

Common runtime artifacts to exclude:
- `kanban.db`, `*.db-shm`, `*.db-wal` — local databases
- `cache/`, `state-snapshots/` — derived/cached data
- `hindsight/`, `*.lock` — session/temp state
- `*.restart_*.json`, `.curator_state` — daemon/runtime metadata
- Per-profile configs with API keys or machine-specific settings

Use the agent's file tools (`write_file`, `patch`) to make changes, then commit:

**Before `git add -A`:** audit untracked files for runtime state (see Pitfall 3). Update `.gitignore` first if needed, and `git rm --cached` any tracked files that should be gitignored (see Pitfall 2).

```bash
# Stage specific files (use -f for gitignored files you intentionally want to track)
git add src/auth.py src/models/user.py tests/test_auth.py

# Commit with a conventional commit message
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware for protected routes
- Add unit tests for auth flow"
```

Commit message format (Conventional Commits):
```
type(scope): short description

Longer explanation if needed. Wrap at 72 characters.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

## 3. Pushing and Creating a PR

### Push the Branch (same either way)

```bash
git push -u origin HEAD
```

### Create the PR

**With gh:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
- Adds login and register API endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

Options: `--draft`, `--reviewer user1,user2`, `--label "enhancement"`, `--base develop`

**With git + curl:**

```bash
BRANCH=$(git branch --show-current)

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{
    \"title\": \"feat: add JWT-based user authentication\",
    \"body\": \"## Summary\nAdds login and register API endpoints.\n\nCloses #42\",
    \"head\": \"$BRANCH\",
    \"base\": \"main\"
  }"
```

The response JSON includes the PR `number` — save it for later commands.

To create as a draft, add `"draft": true` to the JSON body.

## 4. Monitoring CI Status

### Check CI Status

**With gh:**

```bash
# One-shot check
gh pr checks

# Watch until all checks finish (polls every 10s)
gh pr checks --watch
```

**With git + curl:**

```bash
# Get the latest commit SHA on the current branch
SHA=$(git rev-parse HEAD)

# Query the combined status
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Overall: {data['state']}\")
for s in data.get('statuses', []):
    print(f\"  {s['context']}: {s['state']} - {s.get('description', '')}\")"

# Also check GitHub Actions check runs (separate endpoint)
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for cr in data.get('check_runs', []):
    print(f\"  {cr['name']}: {cr['status']} / {cr['conclusion'] or 'pending'}\")"
```

### Poll Until Complete (git + curl)

```bash
# Simple polling loop — check every 30 seconds, up to 10 minutes
SHA=$(git rev-parse HEAD)
for i in $(seq 1 20); do
  STATUS=$(curl -s \
    -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "Check $i: $STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ] || [ "$STATUS" = "error" ]; then
    break
  fi
  sleep 30
done
```

## 5. Auto-Fixing CI Failures

When CI fails, diagnose and fix. This loop works with either auth method.

### Step 1: Get Failure Details

**With gh:**

```bash
# List recent workflow runs on this branch
gh run list --branch $(git branch --show-current) --limit 5

# View failed logs
gh run view <RUN_ID> --log-failed
```

**With git + curl:**

```bash
BRANCH=$(git branch --show-current)

# List workflow runs on this branch
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?branch=$BRANCH&per_page=5" \
  | python3 -c "
import sys, json
runs = json.load(sys.stdin)['workflow_runs']
for r in runs:
    print(f\"Run {r['id']}: {r['name']} - {r['conclusion'] or r['status']}\")"

# Get failed job logs (download as zip, extract, read)
RUN_ID=<run_id>
curl -s -L \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs \
  -o /tmp/ci-logs.zip
cd /tmp && unzip -o ci-logs.zip -d ci-logs && cat ci-logs/*.txt
```

### Step 2: Fix and Push

After identifying the issue, use file tools (`patch`, `write_file`) to fix it:

```bash
git add <fixed_files>
git commit -m "fix: resolve CI failure in <check_name>"
git push
```

### Step 3: Verify

Re-check CI status using the commands from Section 4 above.

### Auto-Fix Loop Pattern

When asked to auto-fix CI, follow this loop:

1. Check CI status → identify failures
2. Read failure logs → understand the error
3. Use `read_file` + `patch`/`write_file` → fix the code
4. `git add . && git commit -m "fix: ..." && git push`
5. Wait for CI → re-check status
6. Repeat if still failing (up to 3 attempts, then ask the user)

## 6. Merging

**With gh:**

```bash
# Squash merge + delete branch (cleanest for feature branches)
gh pr merge --squash --delete-branch

# Enable auto-merge (merges when all checks pass)
gh pr merge --auto --squash --delete-branch
```

**With git + curl:**

```bash
PR_NUMBER=<number>

# Merge the PR via API (squash)
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{
    \"merge_method\": \"squash\",
    \"commit_title\": \"feat: add user authentication (#$PR_NUMBER)\"
  }"

# Delete the remote branch after merge
BRANCH=$(git branch --show-current)
git push origin --delete $BRANCH

# Switch back to main locally
git checkout main && git pull origin main
git branch -d $BRANCH
```

Merge methods: `"merge"` (merge commit), `"squash"`, `"rebase"`

### Enable Auto-Merge (curl)

```bash
# Auto-merge requires the repo to have it enabled in settings.
# This uses the GraphQL API since REST doesn't support auto-merge.
PR_NODE_ID=$(curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/graphql \
  -d "{\"query\": \"mutation { enablePullRequestAutoMerge(input: {pullRequestId: \\\"$PR_NODE_ID\\\", mergeMethod: SQUASH}) { clientMutationId } }\"}"
```

## 7. Complete Workflow Example

```bash
# 1. Start from clean main
git checkout main && git pull origin main

# 2. Branch
git checkout -b fix/login-redirect-bug

# 3. (Agent makes code changes with file tools)

# 4. Commit
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login

Preserves the ?next= parameter instead of always redirecting to /dashboard."

# 5. Push
git push -u origin HEAD

# 6. Create PR (picks gh or curl based on what's available)
# ... (see Section 3)

# 7. Monitor CI (see Section 4)

# 8. Merge when green (see Section 6)
```

## 8. Release Workflow

Complete versioned release pipeline: branch → changes → commit → tag → PR → merge → release.

### Branch and Version Bump

```bash
# Start from clean main
git checkout main && git pull origin main

# Create release branch
git checkout -b release/v0.8.0

# Bump version in pyproject.toml, CHANGELOG.md, AGENTS.md, etc.
# (Delegate to Hefesto or make changes directly)

# Stage ONLY intended files — never git add -A in repos with runtime data
git add pyproject.toml CHANGELOG.md AGENTS.md README.md scripts/ Makefile
git commit -m "release: v0.8.0 — automated setup scripts, docs overhaul"
```

### Tag and Push

```bash
# Create annotated tag
git tag v0.8.0

# Push branch + tag
git push origin release/v0.8.0 --tags
```

### Create PR and Merge

```bash
# Create PR targeting main
gh pr create \
  --base main \
  --head release/v0.8.0 \
  --title "release: v0.8.0 — description" \
  --body "## v0.8.0 — Title

### What's New
- feat: new feature description

### Breaking Changes
- None (or description)

### Migration from v0.7.x
- Run bash scripts/setup.sh"

# Squash merge + delete branch (cleanest for releases)
gh pr merge 25 --squash --delete-branch
```

### Create GitHub Release

```bash
gh release create v0.8.0 \
  --title "v0.8.0 — Title" \
  --notes "## v0.8.0 — Title

### Quick Start
\`\`\`bash
git clone https://github.com/OWNER/REPO.git
cd REPO
bash scripts/setup.sh
\`\`\`

### What's New
- bullet points

### Upgrade from v0.7.x
- Migration instructions"
```

### Post-Release Cleanup

```bash
# Switch back to main and pull the merge
git checkout main
git pull origin main

# Delete local branch (remote already deleted by --delete-branch)
git branch -d release/v0.8.0
```

### Pre-Release Documentation Audit

After any release that removes files, changes installation method, moves paths, or deprecates commands, run a string audit BEFORE tagging. This is a scoped version of the general post-migration audit (see `autonomous-ai-agents/hermes-agent/references/post-migration-audit.md` for the full methodology).

**Quick audit — version consistency and dangling references:**

```bash
# 1. Find references to deleted/moved files in tracked content
git ls-files | xargs grep -l 'configure\.sh\|start\.sh\|olympus_v2\|\.pi-daimons\|~/.hermes/' 2>/dev/null

# 2. Find paths that should be placeholders
grep -rn '/home/[^/]\+/Aether-Agents' --include='*.md' --include='*.yaml' --include='*.html' 2>/dev/null | grep -v '.template'

# 3. Check version badge matches pyproject.toml
grep 'version' pyproject.toml | head -1
grep 'version-' README.md | head -1
grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' CHANGELOG.md | head -1

# 4. Check website references (if applicable)
grep -rn 'pip install -e \.\|configure\.sh\|start\.sh\|~/.hermes/' website/ 2>/dev/null
```

**Full migration audit — after path changes, convention shifts, or module renames:**

For major refactoring (`.eter/` → `.aether/`, profile restructuring, script renaming), follow the comprehensive post-migration audit methodology: catalog old conventions, grep for each pattern, classify by priority (functional code > agent configs > docs > CHANGELOG), fix in order, migrate on-disk state, verify clean. See `references/post-migration-audit.md` in the `hermes-agent` skill.

Fix all findings, commit, then proceed with tagging.

### Pitfalls

- **Never `git add -A`**: Stage specific files only. Repos with runtime data (databases, sessions, caches, local configs) will stage everything. Use `git add <file1> <file2> ...` or `git diff --cached --stat` to review before committing.
- **Version must match everywhere**: pyproject.toml, CHANGELOG.md, AGENTS.md (versioning section), README.md (badge). Miss any one and the release is inconsistent.
- **Tag after commit**: Create the tag AFTER the commit is made, not before. The tag points to the commit hash.
- **Squash merge for releases**: Use `--squash --delete-branch` for release PRs. This keeps main history clean with a single commit per release. Feature branches can use regular merge if needed.
- **Dangling references after cleanup**: When removing deprecated files (scripts, code dirs, docs), always audit for references in README, website, and remaining docs. Deleted code leaves ghost references that confuse new users.

## Useful PR Commands Reference

| Action | gh | git + curl |
|--------|-----|-----------|
| List my PRs | `gh pr list --author @me` | `curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$OWNER/$REPO/pulls?state=open"` |
| View PR diff | `gh pr diff` | `git diff main...HEAD` (local) or `curl -H "Accept: application/vnd.github.diff" ...` |
| Add comment | `gh pr comment N --body "..."` | `curl -X POST .../issues/N/comments -d '{"body":"..."}'` |
| Request review | `gh pr edit N --add-reviewer user` | `curl -X POST .../pulls/N/requested_reviewers -d '{"reviewers":["user"]}'` |
| Close PR | `gh pr close N` | `curl -X PATCH .../pulls/N -d '{"state":"closed"}'` |
| Check out someone's PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |
