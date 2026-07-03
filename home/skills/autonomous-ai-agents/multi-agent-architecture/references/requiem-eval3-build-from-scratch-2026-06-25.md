# Eval 3: Build-from-Scratch (Task Queue System) — 2026-06-25

## Context

After Eval 1 (bug-fixing, Requiem 0/3) and Eval 2 (bug-fixing post-optimization, Requiem 3/3 in 3m23s),
the user terminated the bug-fixing eval format due to clone contamination. He requested a new eval
type: "vamos a medir la capacidad de hacer un producto desde cero y le damos los requerimientos."

## Eval Design

**Task:** Build a Task Queue System from a SPEC.md (82 lines).
- FastAPI + SQLite + Pydantic + async worker
- 6 API endpoints, handler registration, exponential backoff retries
- ~400-600 lines production code, minimum 26 tests
- Exact project structure specified (task_queue/ package, tests/ directory)

**Why this task:**
- Tests decomposition (multiple files, multiple concerns)
- Tests coordination (worker + API must coexist)
- Tests architecture decisions (how to structure async worker with SQLite)
- No existing code to read — pure creation from requirements
- Complex enough to exercise the full pipeline, compact enough for a single session

**Setup:**
- /home/prometeo/eval-requiem/SPEC.md (Raven's copy)
- /home/prometeo/eval-opencode/SPEC.md (OpenCode's copy, identical)
- Same model: glm-5.2
- Raven: HERMES_HOME=/home/prometeo/eval-requiem/raven, launched via original .venv binary
- OpenCode: working in /home/prometeo/eval-opencode

## Venv Portability Issue

Copying Raven's .venv from /home/prometeo/Requiem/raven to /home/prometeo/eval-requiem/raven
failed because .venv contains absolute paths (pyvenv.cfg, bin scripts, .pth files).

**Fix applied:** Use the original project's .venv binary with the new HERMES_HOME:
```
HERMES_HOME=/home/prometeo/eval-requiem/raven /home/prometeo/eval-requiem/raven/.venv/bin/hermes chat --yolo
```
Wait — this still failed initially. The working fix was to copy the .venv AND then use the binary
from that copied venv, but the key was that Hefesto had to do the copy (not Hermes, who is blocked
from running cp/python3 commands). After Hefesto copied everything and replaced paths in config.yaml,
the smoke test (`hermes -z "responde OK" --yolo`) passed.

**Lesson:** Always delegate eval environment setup to Hefesto in one batch. Hermes prepares the
instructions, Hefesto executes the file operations. Then verify with a smoke test before the real run.

## User Interaction Pattern

User said: "no se tu prepara todo y nada mas dime que ejecutar"

This is the preferred workflow for eval setup:
1. Hermes delegates ALL preparation to Hefesto (copy profiles, replace paths, verify venv, create SPEC)
2. Hermes verifies the setup via Hefesto's output
3. Hermes presents the user with ONLY the final launch commands (two terminal commands, one per agent)
4. User runs the commands manually

Do NOT give the user step-by-step instructions to run. Prepare everything, hand over just the commands.

## Observations During Eval 3

Raven's behavior (from user's screen share):
1. Read SPEC.md via read_file_simple (correct — used the rate-limited tool)
2. Loaded necromancer-delegation skill (correct — followed skill-based delegation)
3. Delegated to Necromancer with full SPEC content verbatim (correct — did NOT analyze or pre-resolve)
4. check_progress returned ERROR twice (89.6s and 146.7s waits)
5. Raven re-delegated with more detail (added tests section explicitly)
6. check_progress returned ERROR again (146.7s)
7. Raven was "formulating..." at 23.8K/128K tokens (19%), 7m session, 5m57s active

**Issue to investigate:** check_progress with wait=true is returning errors during long-running
Necromancer tasks. Possible causes:
- State tracker not being updated by the Necromancer's process_task
- Timeout in the wait loop (wait_timeout might be too short for complex builds)
- The Necromancer process itself crashing during decomposition of a large task
- Plugin handler not correctly wiring the state_tracker dict

This is NOT a confirmed bug — it's an active investigation. The eval was interrupted by the
session review request before resolution.

## Launch Commands (for reference)

**OpenCode:**
```
cd /home/prometeo/eval-opencode && opencode
```
First message: "Work autonomously until the project is complete. Do not ask me anything. Do not stop until done. Read the file SPEC.md in this directory. Build the entire system exactly as specified..."

**Raven:**
```
HERMES_HOME=/home/prometeo/eval-requiem/raven /home/prometeo/eval-requiem/raven/.venv/bin/hermes chat --yolo
```
First message: "Work autonomously until the project is complete. Do not ask me anything. Do not stop until done. Read the file SPEC.md at /home/prometeo/eval-requiem/SPEC.md. Build the entire system exactly as specified..."

## Key Difference from Bug-Fixing Evals

Bug-fixing evals test: "understand existing code → find root cause → apply minimal fix"
Build-from-scratch evals test: "understand requirements → design architecture → implement from zero → test"

The build-from-scratch format:
- Stresses decomposition more (multiple files with different concerns)
- Tests architecture decisions (how to structure async worker + SQLite + API)
- No graphify advantage (no existing code to explore)
- Exercises the full pipeline end-to-end (decompose → implement → test → audit)
- May surface different bottlenecks than bug-fixing (e.g., long Necromancer runs)
