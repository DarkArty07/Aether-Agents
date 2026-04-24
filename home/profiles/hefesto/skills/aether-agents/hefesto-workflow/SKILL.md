---
name: hefesto-workflow
description: Hefesto's implementation protocols — receiving specs, role-based sub-agent delegation, code review, integration, and debugging. Includes full Role Catalog.
version: 1.0.0
category: aether-agents
triggers:
  - when hefesto receives a task from hermes
---

# Workflow Context Note

When invoked inside a LangGraph workflow (via `run_workflow`):
- You receive `state["context"]` with accumulated output from previous nodes
- You receive `state["workflow_type"]` indicating which workflow you're in
- Your output becomes input for the next node — write structured, clear output
- HITL checkpoints may follow your output — Christopher will review and decide
- **Do NOT re-do what prior nodes already produced** — use their context directly

When invoked via `talk_to` (direct delegation from Hermes):
- You receive a self-contained prompt with CONTEXT/TASK/CONSTRAINTS/OUTPUT FORMAT
- Follow the protocols in this skill as written
- No context accumulation from other nodes

The output format and protocols remain the same in both cases. The difference is input source (workflow state vs Hermes prompt) and whether your output feeds a downstream node.

# Hefesto Workflow — Implementation Protocols

## When This Skill Loads

Load this skill when Hefesto receives any of these from Hermes:
- Feature implementation request
- Bug fix / debugging task
- Code review request
- Integration task (combining multiple sub-agent outputs)

---

## Protocol 1 — Receiving a Spec

Every task Hefesto receives from Hermes must have: CONTEXT + TASK + CONSTRAINTS + OUTPUT FORMAT.

**If spec is ambiguous, STOP. Do not guess. Report back to Hermes:**
```
CLARIFICATION NEEDED:
[Specific question about the spec]
Cannot proceed until: [what information is missing]
```

**If spec is clear, proceed to Protocol 2.**

---

## Protocol 2 — Role-Based Task Decomposition

Every `delegate_task()` MUST have exactly one role. One role per task. If a task needs two roles, split into two tasks.

### Role Catalog

| Role | Focus | Does NOT do |
|------|-------|-------------|
| `backend` | APIs, DB, models, business logic | UI, deployment, frontend testing |
| `frontend` | UI components, client state, styling | APIs, DB, infra, security |
| `devops` | Infra, CI/CD, deployment, config | Business logic, UI, functional tests |
| `qa` | Testing, edge cases, validation | Implement features, infra, deployment |
| `security` | Sec audit, vulns, hardening, auth | Implement features, UI, deployment |
| `data` | Schema, migrations, queries, optimization | UI, APIs, infra, security |
| `docs` | API docs, READMEs, guides | Implement features, testing, deployment |
| `architect` | Architecture proposals, trade-offs, specs | Implement code, testing, UI |
| `perf` | Load testing, profiling, optimization | UI, docs, security, new features |

**Decomposition steps:**
1. Read the spec
2. List all implementation tasks
3. Assign one role to each task
4. Order tasks by dependency (what must finish before what)
5. Delegate sequentially or in parallel based on dependency

---

## Protocol 3 — Delegate Sub-Agent Template

Every `delegate_task()` call must use this format:

```python
delegate_task(
  role="[ROLE]",
  prompt="""
  ROLE: [same as above — reinforce the role]
  CONTEXT:
  [Tech stack, existing code structure, relevant files, what already exists]

  TASK:
  [Specific, concrete deliverable. Not "implement auth" but "implement JWT middleware that validates Bearer tokens in Authorization header, attaches req.user on success, returns 401 on failure"]

  ACCEPTANCE CRITERIA:
  - [Criterion 1 — testable]
  - [Criterion 2 — testable]
  - [Criterion 3 — testable]

  CONSTRAINTS:
  [No new dependencies unless needed. Follow existing conventions. File locations.]

  OUTPUT:
  [Code files + brief explanation of each decision made]
  """
)
```

---

## Protocol 4 — Code Review

After each sub-agent returns output, Hefesto reviews before integrating:

**Review checklist:**
- [ ] Does code meet every acceptance criterion?
- [ ] Does code follow the existing conventions visible in the codebase?
- [ ] Are there obvious bugs (null refs, missing error handling, wrong types)?
- [ ] Are there security issues Athena would flag (hardcoded secrets, SQL injection risk)?
- [ ] Does it integrate cleanly with adjacent code (no naming conflicts, no circular imports)?

**If review fails:** request revision from the same role with specific feedback.
**If review passes:** proceed to integration.

---

## Protocol 5 — Integration

When combining 2+ sub-agent outputs:
1. Merge code into the project structure
2. Run existing tests — if any fail, debug before continuing
3. Run linting/type checking — fix errors, do not suppress warnings without reason
4. Write or update integration tests if the feature spans multiple components
5. Verify the acceptance criteria from the original spec are all met
6. Report to Hermes: what was built, what was tested, any deviations from spec

---

## Protocol 6 — Systematic Debugging

When debugging, NEVER patch blind. Follow this chain:

```
1. REPRODUCE — What exact steps trigger the bug? What is the exact error message/behavior?
2. ISOLATE — Which component owns this behavior? Narrow the scope.
3. IDENTIFY ROOT CAUSE — Why is this happening? (not just where)
4. FORM HYPOTHESIS — "The bug is caused by X. Fix: Y."
5. FIX — Implement the fix.
6. VERIFY — Does the fix resolve the reproduction case? Do existing tests still pass?
7. REPORT — Root cause + fix + verification result → back to Hermes
```

**Anti-pattern:** Adding a try/catch to silence an error without understanding why it happens is NOT debugging. It is hiding a bug.

---

## Few-Shot Examples

### Example A — Feature Decomposition

Hermes sends:
```
CONTEXT: Express.js API, PostgreSQL, TypeScript. Adding JWT authentication.
TASK: Implement complete auth flow: register, login, JWT issue, protected route middleware.
CONSTRAINTS: Use jsonwebtoken library. No OAuth. Passwords hashed with bcrypt.
```

Hefesto decomposes:
```
Tasks:
  1. [data] Create users table migration + User model
  2. [backend] Implement /auth/register and /auth/login endpoints
  3. [backend] JWT issue on login + refresh token flow
  4. [backend] Auth middleware for protected routes
  5. [qa] Integration tests for all 4 flows

Order: 1 → 2 → 3 → 4 → 5 (sequential, each depends on previous)
```

---

### Example B — Debugging

Hermes reports: "Login works but JWT validation in middleware is returning 401 even with valid tokens."

Hefesto:
```
REPRODUCE:
- POST /auth/login → 200, receives token
- GET /api/user (with Bearer token) → 401

ISOLATE:
- Middleware is the component — narrow to: token extraction, token verification, or req.user assignment

HYPOTHESES:
1. Token extracted incorrectly (header parsing issue)
2. JWT_SECRET mismatch between login signing and middleware validation
3. Token expiry set too short

ROOT CAUSE FOUND:
JWT_SECRET in .env is "my_secret" but middleware reads process.env.JWT_SECRET which is undefined in test environment.
Fix: Add JWT_SECRET to .env.test

VERIFY:
- Tests passing after fix
- Login + protected route flow works end-to-end
```

---

### Example C — Sub-Agent Delegation

```python
delegate_task(
  role="backend",
  prompt="""
  ROLE: backend
  CONTEXT:
  Express.js 4, TypeScript, PostgreSQL via pg library. Auth middleware already exists at src/middleware/auth.ts.
  Existing route pattern: src/routes/[name].routes.ts, handler in src/controllers/[name].controller.ts.

  TASK:
  Implement GET /api/user/profile — returns authenticated user's profile data.
  Reads: id, email, created_at, display_name from users table.
  Requires: valid JWT (middleware already handles rejection).
  Returns: { id, email, display_name, created_at } as JSON.

  ACCEPTANCE CRITERIA:
  - Returns 200 with user object for valid JWT
  - Returns user's own data only (no other users accessible)
  - display_name can be null — handle gracefully (return null, not 500)

  CONSTRAINTS:
  No new libraries. Follow existing route/controller structure. SQL query in controller, not raw ORM.

  OUTPUT:
  src/routes/user.routes.ts + src/controllers/user.controller.ts + brief note on any edge cases handled.
  """
)
```
