# Daimon Delegation Patterns

When delegating tasks to Daimons (Hefesto, Etalides, etc.), choose blocking vs background mode based on expected duration and user interaction needs.

## Blocking Delegation (Default)

Use when:
- Task expected to complete in <5 minutes
- User needs result before proceeding
- Simple, well-scoped work

```python
result = talk_to(
    action="delegate",
    agent="hefesto",
    prompt="Implement feature X...",
    timeout=300  # 5 minutes
)
# Wait for result, then continue
```

**Risk**: If task exceeds timeout, session is lost and you cannot resume.

## Background Delegation (Long-Running Tasks)

Use when:
- Task expected to take >5 minutes (multi-phase implementations, large refactors)
- User wants to continue working on other things
- Task has multiple phases that may exceed single timeout

```python
# Start Daimon in background
hefesto_session = talk_to(
    action="open",
    agent="hefesto",
    project_root="/path/to/project"
)

# Send task (non-blocking)
talk_to(
    action="message",
    session_id=hefesto_session["session_id"],
    prompt="Implement 5-phase migration..."
)

# Tell user you'll notify when done
print("Hefesto working in background. I'll let you know when complete.")

# Continue working with user on other tasks...
# [Other conversation happens here]

# Later: check status periodically or wait for user to ask
status = talk_to(action="poll", session_id=hefesto_session["session_id"])
if status["status"] == "completed":
    result = status["last_turn"]
    # Present result to user
```

**Key pattern**: Hermes continues interacting with user while Daimon works independently.

## Monitoring Background Tasks

### Option 1: Cron Job (Automated)

For tasks that will take 10-30 minutes:

```python
# Create monitoring job
cronjob(
    action="create",
    name="monitor-hefesto-session",
    schedule="every 60s",
    prompt=f"""Check Hefesto session {session_id} status.
If completed: notify user with summary, then remove this cron job.
If still running: do nothing (silent).
If failed: notify user with error, then remove this cron job.""",
    repeat=30  # Max 30 checks (30 minutes)
)
```

### Option 2: Manual Polling (User-Driven)

When user asks "how's it going?":

```python
status = talk_to(action="poll", session_id=session_id)
print(f"Status: {status['status']}")
print(f"Tool calls: {status['tool_calls']}")
print(f"Last action: {status['last_turn']}")
```

### Option 3: Completion Callback

If user says "let me know when done":

```python
# Store session ID for later
background_task = {
    "session_id": hefesto_session["session_id"],
    "description": "Honcho integration phases 3-5",
    "started_at": now()
}

# When user asks or at natural break point:
status = talk_to(action="poll", session_id=background_task["session_id"])
if status["status"] == "completed":
    print("Hefesto finished! Here's what was done:")
    print(status["last_turn"])
```

## Timeout Recovery

If blocking delegation times out:

1. **Check what was completed**: Poll the session or check filesystem for artifacts
2. **Resume from checkpoint**: Open new session with context about what's done
3. **Break into smaller chunks**: Delegate remaining phases separately

```python
# After timeout on 5-phase task
print("Task exceeded 600s timeout. Checking progress...")

# Check filesystem for completed work
if exists("PATCHES.md") and exists(".env.template"):
    print("Phases 1-2 completed. Resuming phases 3-5...")
    
    # New delegation with narrower scope
    talk_to(
        action="delegate",
        agent="hefesto",
        prompt="Complete phases 3-5 of Honcho integration. Phases 1-2 are done (PATCHES.md and .env.template exist).",
        timeout=600
    )
```

## Decision Framework

Ask yourself:
1. **How long will this take?** 
   - <5 min → blocking
   - 5-30 min → background + manual polling
   - >30 min → background + cron monitoring

2. **Does user need to wait?**
   - Yes (blocking dependency) → blocking delegation
   - No (can continue other work) → background delegation

3. **Can task be broken into chunks?**
   - Yes → multiple smaller blocking delegations
   - No → single background delegation

## Example: Multi-Phase Integration

User: "Integrate Honcho as memory provider. Here's the 5-phase plan..."

**Wrong approach**:
```python
talk_to(action="delegate", prompt="All 5 phases...", timeout=600)
# Times out after phase 2, session lost, cannot resume
```

**Right approach**:
```python
# Option A: Background delegation
session = talk_to(action="open", agent="hefesto", project_root="...")
talk_to(action="message", session_id=sid, prompt="All 5 phases...")
print("Hefesto working on Honcho integration (5 phases). I'll check in periodically.")

# Continue with user...
# [User asks about something else]
# [10 minutes pass]

# Check status
status = talk_to(action="poll", session_id=sid)
if status["status"] == "completed":
    print("Honcho integration complete!")
    print(status["last_turn"])

# Option B: Phased delegation
talk_to(action="delegate", prompt="Phases 1-2...", timeout=300)  # Quick setup
# Report: "Phases 1-2 done"
talk_to(action="delegate", prompt="Phases 3-5...", timeout=600)  # Main work
# Report: "All phases complete"
```