# ACP Stall Diagnosis and Fix

## Symptom
Daimon delegation returns empty result: `thoughts: 0, messages: 0, tool_calls: 0`. The Daimon appears to be running but produces no output.

## Root Cause (v0.8.2 Fix)
The `_get_session_id()` function in `olympus_v3_hooks/hooks.py` reads PID-suffixed session files incorrectly. It checks for `.olympus_session` (without PID) but `acp_manager.py` writes `.olympus_session.{PID}` (with PID suffix). The function returns `None`, causing all plugin hooks to skip writing turn data.

## Diagnosis Pattern
1. Check for `.olympus_session.{PID}` files in `HERMES_HOME/`: `ls $HERMES_HOME/.olympus_session.*`
2. If PID-suffixed files exist but `_get_session_id()` returns None, the bug is present
3. Legacy `.olympus_session` (no PID) files are fallbacks that mask the bug

## Fix
The `_get_session_id()` function must check for PID-suffixed files first:
```python
def _get_session_id():
    pid = os.getpid()
    # 1. Check PID-suffixed file first (concurrent-safe)
    pid_file = Path(home) / f".olympus_session.{pid}"
    if pid_file.exists():
        return pid_file.read_text().strip()
    # 2. Fallback to generic file (backward compatible)
    generic_file = Path(home) / ".olympus_session"
    if generic_file.exists():
        return generic_file.read_text().strip()
    # 3. Environment variable
    return os.environ.get("OLYMPUS_SESSION_ID")
```

## Prevention
- Always test delegation after changes to hook files
- Run `hermes doctor` after any olympus_v3 update
- Gitignore PID-suffixed runtime files