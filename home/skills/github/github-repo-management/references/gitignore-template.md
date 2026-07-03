# Standard .gitignore Template

A comprehensive starting `.gitignore` for Python-based projects. Copy and modify as needed.

```gitignore
# Secrets — MUST be first section so secrets never reach the index
.env
*.env
.env.*

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/

# SQLite
*.db
*.db-journal

# Node (if using frontend tooling)
node_modules/
npm-debug.log*

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Caches
.cache/
.pytest_cache/
.mypy_cache/
```

## Project-Specific Additions

Add below the common section for project-specific ignores:

```gitignore
# Project-specific
state.db
*.log
output/
data/raw/
```

## Verification

After creating `.gitignore` and running `git init && git add .`, verify nothing slipped through:

```bash
git status --ignored --short
```

Any files listed under the ignored section should be expected. If you see `.env`, `.venv/`, `node_modules/`, or `*.db` files **not** in the ignored section, the `.gitignore` needs fixing — reset with `git rm -r --cached . && git add .`.
