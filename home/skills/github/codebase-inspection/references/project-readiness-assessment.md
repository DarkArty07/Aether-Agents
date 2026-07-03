# Project Readiness Assessment

Structured approach to evaluate a project's actual state vs. its documented goals. Use when the user asks "what state is this project in?", "is this ready to ship?", or "what's missing?".

## Assessment Checklist

Run these in order — each builds on the previous:

### 1. Version Control State
```bash
cd /path/to/project
git status
git log --oneline -10
git remote -v
git branch -a
```
- Is the working tree clean?
- How active is development? (commit frequency, dates)
- Is it pushed to a remote?

### 2. Code Structure
```bash
find . -maxdepth 2 -type f -name "*.py" | head -40   # adjust extension
find . -name "*.py" -exec wc -l {} + | sort -n | tail -20
```
- What's the tech stack? (check requirements.txt, package.json, etc.)
- What's the directory structure? (layers, modules)
- What's the code volume? (~LOC per module)

### 3. Test Health
```bash
python -m pytest --tb=short -q 2>&1 | tail -10
# or: npm test, cargo test, etc.
```
- How many tests pass/fail?
- Are there integration tests? Unit tests?
- Any collection errors?

### 4. Documentation vs Reality
- Read the roadmap/README/changelog
- Cross-reference: which documented features actually exist in code?
- Identify: what's implemented but not documented? What's documented but not implemented?

### 5. Gap Analysis
For each missing piece, assess:
- **Critical**: blocks the core user experience
- **Important**: needed for production but not for demo
- **Nice-to-have**: polish, optimization

## Output Format

Present results as:
```
ESTADO ACTUAL DEL PROYECTO

Backend:
  [OK] System A
  [OK] System B
  [!!] System C (tests failing)
  [--] System D (not implemented)

Frontend: EXISTS / NOT FOUND

Tests: X passing, Y failing, Z errors

RESUMEN: One-paragraph summary of readiness level.

FALTAN: Prioritized list of what's needed to reach goal.
```

## Pitfalls

1. **Don't just count LOC** — a 10K LOC project with 0 tests is less ready than a 2K LOC project with 200 tests. Quality > quantity.
2. **Check if tests actually run** — don't trust test file existence. Run them.
3. **Roadmap dates are aspirational** — compare features, not timelines.
4. **Missing frontend is often the biggest gap** — a working backend with no UI is not playable.
5. **Read the .env.example** — tells you what external services are needed (API keys, DB, etc.)
