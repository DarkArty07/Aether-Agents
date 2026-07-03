# End-to-End Eval Methodology for Multi-Agent Systems

How to evaluate a multi-agent coding system (like Requiem Agents) with real,
controlled, verifiable problems — NOT synthetic benchmarks.

## Why Not SWE-bench or Preset Datasets

The user explicitly rejects preset benchmarks (SWE-bench, HumanEval, etc.) for
evaluating custom multi-agent systems. Reasons:

1. **Different architecture**: SWE-bench tests single-model code generation.
   Requiem tests a hierarchical pipeline (assistant → orchestrator → workers →
   auditor). The bottleneck is coordination, not just code generation.
2. **Different tooling**: Requiem uses graphify for code understanding, custom
   tool calling, and a peer-auditor. SWE-bench instances don't exercise these.
3. **No real stakes**: Preset problems have known answers. The user wants to
   discover if the system can handle problems where the answer is NOT in the
   training data — real bugs in the actual project code.

## Methodology: Real Bugs as Eval Cases

### Step 1: Scan the codebase for genuine bugs

Use static analysis to find real issues in the project:

```bash
# Bare excepts and broad exception catches
grep -rn "except:" --include="*.py" | grep -v __pycache__ | grep -v .venv
grep -rn "except Exception" --include="*.py" | grep -v __pycache__ | grep -v .venv

# Silent failures (except + pass)
grep -rn "pass$" --include="*.py" | grep -v __pycache__ | grep -v .venv

# TODOs, FIXMEs, HACKs
grep -rn "TODO\|FIXME\|HACK\|XXX\|BUG" --include="*.py"

# Missing error handling in API endpoints
# Connection leaks (open without close)
# Logic bugs (string matching for pass/fail, etc.)
```

### Step 2: Classify candidates by difficulty

| Level | Criteria | Example |
|-------|----------|---------|
| Easy | Single function, clear bug, local fix | parse_verdict() logic error in revenant.py |
| Medium | Cross-file, needs understanding of data flow | Dashboard API connection leak between server.py and eval.py |
| Hard | Architectural, multiple interacting components | Adding a new endpoint that queries the DB with proper connection lifecycle |

### Step 3: Create GitHub issues

Each bug becomes a GitHub issue with:
- Clear description of the expected vs actual behavior
- File paths and line numbers
- NO solution hints — the system must find and fix it

```bash
gh issue create --title "Bug: parse_verdict() returns wrong result for mixed PASS/FAIL text" \
  --body "Description..."
```

### Step 4: Run the full pipeline

Give each issue to the assistant (Raven) as a task using the structured
delegation template (OBJETIVO/CONTEXTO/RESTRICCIONES/CRITERIOS DE ACEPTACION).

The pipeline exercises:
1. **Graphify exploration** — does Raven query the graph to understand the code?
2. **Delegation** — does delegate_to_necromancer fire with a well-formed prompt?
3. **Decomposition** — does Necromancer break it into subtasks?
4. **Execution** — do Shades write code that compiles?
5. **Audit** — does Revenant catch errors? Does it pass correct code?
6. **Presentation** — does Raven synthesize results for the user?

### Step 5: Measure

For each eval case, record:

| Metric | How to measure |
|--------|---------------|
| **Wall-clock time** | `date` before and after |
| **Raven found the bug with graphify** | Check if query_graph was called |
| **Necromancer decomposed correctly** | Check telemetry DB for decomposition entries |
| **Shade code compiles** | `python3 -m py_compile` on modified files |
| **Revenant audit result** | Telemetry DB: pass/fail/escalated |
| **Fix is correct** | Run a verification test (pre-written by the evaluator) |
| **Tokens consumed** | Sum from telemetry DB |
| **Cost** | Sum of cost_usd from telemetry DB |
| **Retries needed** | Count of audit fail entries before pass |
| **Escalations** | Count of escalated entries |

### Step 6: Verify independently

The evaluator (human or orchestrator) writes a test or verification script
BEFORE running the eval. After the pipeline completes:

```bash
# Did the fix compile?
python3 -m py_compile <modified_file>

# Does the fix actually work?
python3 -m pytest tests/test_<bug_name>.py -v

# Did the fix introduce regressions?
python3 -m pytest tests/ -v
```

## Autonomous Batch Execution Pattern

When the user says "hazlo todo de manera autónoma," execute the full plan
without HITL gates:

1. **Batch by phase** — group tasks into phases (critical → high → medium → low)
2. **Single delegation per phase** — send all tasks in a phase to Hefesto in one
   delegate call with numbered tasks and clear specs
3. **Verify after each batch** — run `python3 -m py_compile` on all modified
   files before proceeding to the next phase
4. **Don't retry failed delegations silently** — if Hefesto times out or returns
   error, check what was completed (grep/compile), then re-delegate only the
   remaining tasks
5. **Commit at the end** — single commit with all changes, clean .gitignore first
6. **Report when done** — show compile status + git commit hash

Key: the verification between phases is ORCHESTRATOR-driven (terminal grep +
py_compile), not Daimon-driven. The orchestrator checks file state directly.

## Comparative A/B Eval: Two Agents, Same Bugs

When the user wants to compare two coding agents (e.g., Requiem vs OpenCode),
use a comparative setup with identical conditions:

### Setup

1. **Clone the repo twice** — one working copy per agent:
   ```bash
   git clone /path/to/project /home/eval-agent-a
   git clone /path/to/project /home/eval-agent-b
   ```
   The clones must NOT include .venv, node_modules, or caches — just the
   source code and git history.

2. **Create GitHub issues** — real bugs found via static analysis (Step 1
   above). Issues must describe the symptom without hinting at the fix.
   Acceptance criteria should specify test file names so both agents create
   the same test artifacts.

3. **Write a PROMPT.md for each agent** — tailored to the agent's interface:
   - For a CLI agent (OpenCode): "read issues with gh, investigate, fix,
     write tests, verify with py_compile + pytest, commit each fix separately"
   - For a multi-agent system (Requiem): "use graphify to explore, delegate
     with structured template, monitor with check_progress, present results"

4. **Same model for both** — the user configures the same LLM model in both
   agents. This isolates the architecture as the variable.

5. **Write EVAL.md** — a results table with per-issue metrics:
   time, tokens in/out, cost, tests created, tests pass, compiles, fix correct,
   attempts/retries.

### Bug Selection Criteria for Comparative Eval

Each bug should exercise different capabilities:

| Type | What it tests | Example |
|------|---------------|---------|
| Logic bug | Reasoning about control flow | parse_verdict() fallback prioritization |
| Resource bug | Understanding cross-file data flow | SQLite connection leak between modules |
| Information loss | Recognizing silent failures | Broad except swallowing useful output |

### Running the Eval

Both agents run in parallel (separate working directories, no interference).
The user launches each agent manually with its PROMPT.md.

### Verification

After both agents complete, verify each fix independently:
```bash
# For each agent's working directory:
cd /home/eval-agent-a  # or eval-agent-b
python3 -m py_compile <modified_files>
python3 -m pytest tests/ -v
git diff  # manual review of the actual fix
```

### Victory Criteria

1. Most issues fixed correctly
2. Tie-breaker: least total time
3. Tie-breaker: least total cost
4. Tie-breaker: most tests created and passing

## Common Pitfalls

- **Don't use bugs you've already fixed** — the system might have learned from
  the fix in a previous session. Find NEW bugs.
- **Don't hint at the solution in the issue** — the issue describes the symptom,
  not the fix. Let the system diagnose.
- **Pre-write verification tests** — the evaluator writes the acceptance test
  BEFORE running the eval, so pass/fail is objective.
- **Same conditions every time** — same model, same config, same graph. Don't
  change settings between eval runs.
- **Measure what matters** — "did it compile" is necessary but not sufficient.
  "Did the fix actually solve the bug" is the real metric.
- **Separate working directories for comparative eval** — never run two agents
  in the same directory. Clone the repo twice to prevent interference.
- **Don't give the agents the answers** — the issue describes the bug, not the
  fix. The PROMPT.md says "fix these bugs" without hints. The user's preference:
  "problemas REALES, controlados y con respuesta" — real problems, controlled
  conditions, with known answers (for the evaluator, not the agent).
- **Prompts must say "work autonomously, do not ask, do not stop until done"** —
  without this, agents may pause for user input mid-task. The prompt should
  explicitly state: "Work completely alone, no user interaction needed. If you
  get stuck, try a different approach. Do not ask for help."
- **Keep copies of the original repo for diff comparison** — after cloning,
  make an additional copy (eval-agent-original) as a pristine baseline. This
  allows `diff -r eval-agent-original eval-agent` to verify exactly what changed.
- **The multi-agent system may work on the wrong directory** — if the config
  or prompt references the original project path instead of the eval clone,
  changes go to the wrong place. In the Requiem eval, Raven's delegate_task
  calls referenced /home/prometeo/Requiem (the original) instead of
  /home/prometeo/eval-requiem (the eval clone), meaning all Shade work went
  to the wrong repo. This was only visible in the delegate log:
  "Run the command: gh issue view 1 in the repository at /home/prometeo/Requiem."
  Fix: verify the working directory BEFORE starting the eval by checking:
  (1) the agent's config.yaml project_root, (2) the first delegate_task log
  line for the actual path used. The PROMPT.md should explicitly state the
  working directory path to avoid ambiguity.
- **Keep pristine copies for diff comparison** — after cloning, make additional
  copies (eval-agent-original) as baselines. This allows
  `diff -r eval-agent-original eval-agent` to verify exactly what changed.
  Also useful for re-running the eval after optimizations without re-cloning.
- **The eval prompt must request fully autonomous work** — without an explicit
  instruction like "Work autonomously until all 3 bugs are fixed. Do not ask
  me anything. Do not stop until done.", agents may pause for user input
  mid-task. The prompt must also say "If you get stuck, try a different
  approach. Do not ask for help." to prevent the agent from stalling on
  clarification requests.
- **Clone from GitHub remote, not local repo, to avoid fix contamination** —
  when re-running an eval after fixes have been committed locally, cloning
  from the local repo includes the fix commits. The agent discovers the code
  is already fixed, investigates why issues are still open (local commits not
  pushed to GitHub), and verifies tests pass without writing new code —
  producing a meaningless eval. Fix: either clone from the GitHub remote
  (which doesn't have the fix commits), or reset the clone to a known
  pre-fix commit: `git reset --hard <pre-fix-commit-sha>`.
- **Multi-agent agent launch uses HERMES_HOME, not --config** — hermes-agent
  profiles with custom SOUL.md (like Raven) are launched via
  `HERMES_HOME=/path/to/raven hermes chat --yolo`. The --config flag does not
  exist. The --yolo flag enables autonomous mode (no confirmation prompts),
  which is essential for evals where the agent must work without user
  interaction.
- **Build-from-scratch evals test different capabilities than bug-fixing
  evals** — bug fixing tests "understand existing code, find root cause,
  apply minimal fix." Build-from-scratch tests "understand requirements,
  design architecture, implement from zero, test." The latter stresses
  decomposition and coordination more thoroughly. When designing a
  build-from-scratch eval, provide requirements (not issues) and measure:
  architecture quality, code organization, test coverage, time-to-working,
  and how well the result matches the requirements.
