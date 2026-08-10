# Aether Agents External Coding Agent Operating Contract

> **Status:** CURRENT
> **Product owner:** Christopher (DarkArty07)
> **Orchestrator and acceptance owner:** Hermes
> **Project root:** `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition`

## 1. Authority

- The user owns product meaning, priorities, material compromises, protected
  effects and final acceptance.
- Hermes owns task decomposition, architecture interpretation, exact scope,
  verification, acceptance classification and the next handoff.
- The external coding agent implements only the one active task file. It may not
  amend product intent, reinterpret later milestones as authorized, accept its own
  work or continue autonomously.
- Version-controlled product decisions, `AGENTS.md`, the active task and this
  contract outrank assumptions inferred from code or tool availability.

## 2. Exact repository boundary

All repository work must occur inside:

```text
/home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-transition
```

Do not create implementation copies in another checkout, home directory, `/tmp`,
Desktop project, or unrelated repository. Temporary test files are allowed only
when the active task explicitly permits them and they are cleaned before report.

Before writing, verify the exact branch, clean tree, HEAD relationship and handoff
subject required by the active task. If any preflight fact differs, stop with
`BLOCKED` instead of resetting, stashing, switching or absorbing changes.

## 3. Git permissions

Allowed:

- inspect status, history and diffs read-only;
- create only the task-authorized English Conventional Commits;
- use multiple atomic commits only when the task names their boundaries.

Forbidden:

- push, pull, fetch, merge, rebase, amend, cherry-pick or force operations;
- create, delete, rename or switch branches or worktrees;
- tags, GitHub Releases, PRs, issues or other remote mutations;
- reset, restore, clean, stash or discard pre-existing work;
- modify the committed task or this operating contract during execution.

The worktree must be clean after the final task commit. A report is part of the
required deliverable, not an untracked afterthought.

## 4. Protected state and secrets

Never read, print, copy, hash, modify, migrate, truncate or delete:

- `.aether/` continuity or database state outside this tracked worktree;
- any `.env`, credentials, tokens, API keys, cookies, browser profiles or auth
  stores;
- live `home/profiles/*/config.yaml`, generated user configuration or private
  profile state;
- installed provider account data, global Orca state or historical local stores;
- another project, checkout or repository.

Do not add real secrets to fixtures. Synthetic canaries must be unmistakably fake.
Do not print complete environment variables, process environments or credential-
bearing command lines. If a required credential or protected read would be
necessary, report `BLOCKED`; do not substitute fabricated output.

## 5. Runtime and external effects

The active task defines the exact allowed effects. Unless it explicitly says
otherwise, do not:

- start, restart, stop or signal services or processes;
- open GUI applications or use browser/computer automation;
- create Orca Runs, Tasks, Dispatches, workers, terminals or worktrees;
- call model/provider/network APIs or incur cost;
- install or update packages, binaries, plugins, profiles or configuration;
- migrate data, activate runtime wiring, deploy or publish.

Read-only process inventory is allowed when required for evidence. Never kill an
unknown process. A missing capability is a blocker, not authorization to weaken a
gate.

## 6. Implementation discipline

1. Read `AGENTS.md`, this contract, the active task and every source contract the
   task names before writing.
2. Use strict RED-GREEN-REFACTOR for behavior changes. Record the exact RED command
   and expected failure before production code exists.
3. Implement the smallest coherent behavior that satisfies the task. Do not add
   compatibility shims, hidden fallback, speculative abstractions or future
   milestone placeholders.
4. Preserve unrelated files and existing tests. Never weaken, skip, delete or
   retry tests merely to obtain green output.
5. Use only dependencies already present unless the active task explicitly
   authorizes a dependency change. Network installation is forbidden by default.
6. Treat stdout, JSON receipts, commits and reports as public project evidence:
   deterministic, secret-free and honest about unknowns.
7. After three failed attempts using the same approach, stop and report the actual
   blocker with preserved evidence.

## 7. Mandatory report

Create the exact report path named by the active task using this schema:

```text
STATUS: PASS | FAIL | BLOCKED
COMMITS:
- <full hash> <subject> for every commit that precedes this report
- current report commit: <required subject and parent>; return its actual hash after commit
FILES:
- <created/modified/deleted path>
RED:
- <exact command> — <expected failing result>
TESTS:
- <exact command> — <actual exit/result/count>
SMOKE:
- <exact step> — <observable result>
IDENTITY/EVIDENCE:
- <task-specific immutable facts and artifact paths>
DECISIONS:
- none | <unresolved material choice>
BLOCKERS:
- none | <exact blocker>
REMAINING RISKS:
- <concrete residual risk>
SCOPE CONFIRMATION:
- active task only
- next milestone not started
- protected paths not accessed or modified
- no push/merge/rebase/amend/tag/Release
```

`PASS` means implementer-reported provisional pass. Only Hermes may independently
accept the task after inspecting commits, code, tests and reproduced behavior.
The report must not attempt to embed the hash of the commit that contains the
report itself; that hash belongs in the agent's post-commit return message.

## 8. Stop condition

After the required report and authorized local commits exist:

1. verify the worktree is clean;
2. print only the concise report summary requested by the active task;
3. stop completely.

Do not propose or begin the next milestone. Hermes will inspect the repository and
either accept the task, issue one focused correction task, or classify a blocker.
